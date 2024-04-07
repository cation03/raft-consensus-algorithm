import threading
import time
import os
import utils
from config import cfg
import grpc
import server_pb2
import server_pb2_grpc

FOLLOWER = 0
CANDIDATE = 1
LEADER = 2

class Node():
    def __init__(self, fellow, my_ip):
        self.addr = my_ip
        self.DB = {}
        self.log = []
        self.lock = threading.Lock()
        self.staged = None
        self.term = 0
        self.node_id = int(str(my_ip)[-1])
        self.voteCount = 0
        self.status = FOLLOWER
        self.commitIdx = 0
        self.timeout_thread = None
        self.fellow = fellow
        self.majority = ((len(self.fellow) + 1) // 2) + 1
        self.lease_timer = None  # Lease timer
        self.lease_acquisition_allowed = True  # Flag to indicate if lease acquisition is allowed
        self.init_timeout()
        self.create_log_folder()
        self.initiate_metadata()

    def create_log_folder(self):
        log_folder = f"logs_node_{self.node_id}"
        os.makedirs(log_folder, exist_ok=True)
        self.log_file = os.path.join(log_folder, "logs.txt")
        self.dump_file = os.path.join(log_folder, "dump.txt")
        self.metadata_file = os.path.join(log_folder, "metadata.txt")
        self.dump_logs("Node initialized")

    def dump_logs(self, message):
        with open(self.dump_file, "a") as f:
            f.write(f"{message}\n")

    def append_to_log(self, message):
        with open(self.log_file, "a") as f:
            f.write(f"{message}\n")

    def append_metadata(self, message):
        with open(self.metadata_file, "a") as f:
            f.write(f"{message}\n")

    def initiate_metadata(self):
        with open(self.metadata_file, "w") as f:
            f.write(f"0 {self.term} None\n")

    def incrementVote(self):
        self.voteCount += 1
        self.append_metadata(f"{self.commitIdx} {self.term} {self.node_id}")
        if self.voteCount >= self.majority:
            self.status = LEADER
            self.startHeartBeat()
            
            self.dump_logs(f"Node {self.addr} became the leader for term {self.term}")
            print(f"{self.addr} becomes the leader of term {self.term}")
        else:
            print(f"{self.node_id} voted for {self.addr} in term {self.term}")
            self.dump_logs(f"{self.node_id} voted for {self.addr} in term {self.term}")

    def startElection(self):
        self.status = CANDIDATE
        self.voteCount = 0
        self.term += 1
        # self.initiate_metadata()  # Reset metadata file for new term
        self.init_timeout()
        self.incrementVote()
        self.send_vote_req()

    def send_vote_req(self):
        for voter in self.fellow:
            threading.Thread(target=self.ask_for_vote, args=(voter, self.term)).start()
            
    def ask_for_vote(self, voter, term):
        message = {
            "commitIdx": self.commitIdx,
            "term": term,
            "staged": self.staged
        }
        voter_id = self.node_id
        route = "vote_req"

        while self.term == term and self.status == CANDIDATE:
            reply = utils.send(voter, route, message)
            if reply:
                voter_id = int(str(voter)[-1])  # Extract voter's node ID from its IP address
                choice = reply.json()["choice"]
                if choice is not None:
                    self.incrementVote()
                    # vote_info = f"Voted for Node {voter_id} in term {term}, commitIdx {self.commitIdx}"
                    # print(vote_info)
                    # self.append_to_log(vote_info)  # Add vote information to the logs
                    # Append metadata indicating the voted node's ID
                elif not choice:
                    term = reply.json()["term"]
                    self.log_vote_denied(voter_id, term)
                    if self.term < term:
                        self.status = FOLLOWER
                        self.term = term
                        # self.append_to_log(f"Received higher term {term}, converting to follower")
                        break
            break
        self.append_metadata(f"{self.commitIdx} {term} {voter_id}")

    # some other server is asking
    def decide_vote(self, term, commitIdx, staged):
        bool_condition = (staged or (self.staged == staged))
        if self.term < term and self.commitIdx <= commitIdx and bool_condition:
            self.reset_timeout()
            self.term = term
            return True, self.term
        else:
            return False, self.term

    def startHeartBeat(self):
        self.dump_logs(f"Leader {self.addr} sending heartbeat & Renewing Lease")
        print("Starting HEARTBEAT")
        if self.staged:
            self.handle_put(self.staged)

        if self.lease_acquisition_allowed:
            self.start_lease_timer()
            self.replicate_lease_interval()

        for each in self.fellow:
            t = threading.Thread(target=self.send_heartbeat, args=(each,))
            t.start()

    def start_lease_timer(self):
        self.lease_timer = threading.Timer(cfg.LEASE_INTERVAL, self.renew_lease)
        self.lease_timer.start()

    def renew_lease(self):
        self.dump_logs(f"Leader {self.addr} lease renewal failed. Stepping Down.")
        print(f"Leader {self.addr} lease renewal failed. Stepping Down.")
        self.lease_acquisition_allowed = True
        if self.status == LEADER:

            self.status = FOLLOWER
            self.init_timeout()
            self.dump_logs(f"New leader waiting for old leader lease to timeout.")
            print(f"Leader {self.addr} has stepped down. Starting election.")
            self.startElection()
            self.dump_logs(f"Node {self.addr} election timer timed out. Starting election.")

    def replicate_lease_interval(self):
        for follower in self.fellow:
            threading.Thread(target=self.send_lease_interval, args=(follower,)).start()

    def send_lease_interval(self, follower):
        route = "lease_interval"
        message = {"interval": cfg.LEASE_INTERVAL}
        utils.send(follower, route, message)

    def update_follower_commitIdx(self, follower):
        first_message = {"term": self.term, "addr": self.addr}
        second_message = {
            "term": self.term,
            "payload": self.log[-1],
            "addr": self.addr,
            "action": "commit",
        }
        route = "heartbeat"
        
        reply = utils.send(follower, route, first_message)
        
        if reply is not None:
            if reply.json()["commitIdx"] < self.commitIdx:
                reply = utils.send(follower, route, second_message)

    def send_heartbeat(self, follower):
        if self.log:
            self.update_follower_commitIdx(follower)

        route = "heartbeat"
        message = {"term": self.term, "addr": self.addr}
        while self.status == LEADER:
            reply = utils.send(follower, route, message)
            start = time.time()
            if reply:
                self.heartbeat_reply_handler(reply.json()["term"],
                                             reply.json()["commitIdx"])
            curr_time = time.time()
            delta = curr_time - start
            diff = cfg.HB_TIME - delta
            time.sleep(diff / 1000)
        self.append_to_log(f"NO-OP {self.term}")

    def heartbeat_reply_handler(self, term, commitIdx):
        if self.term < term:
            self.status = FOLLOWER
            self.term = term
            self.init_timeout()

    def reset_timeout(self):
        self.election_time = time.time() + utils.random_timeout()

    def heartbeat_follower(self, msg):
        term = msg.get("term")
        if self.term <= term:
            self.leader = msg.get("addr")
            self.reset_timeout()
            if self.status == CANDIDATE:
                self.status = FOLLOWER
            elif self.status == LEADER:
                self.status = FOLLOWER
                self.init_timeout()
            if term > self.term:
                self.term = term

            if "action" in msg:
                self.dump_logs(f"Node {self.addr} (follower) received an {msg['action']} request")
                print("received action", msg)
                # append to log only if action is commit
                if msg["action"] == "commit":
                    self.append_to_log(f"SET {msg['payload']['key']} {msg['payload']['value']} {self.term}")
                    # also append to the leader's log
                if msg["action"] == "log":
                    self.staged = msg.get("payload")
                    self.log_follower_accepted_append_entry(self.addr, msg.get("addr"))
                elif msg.get("commitIdx") is not None and self.commitIdx <= msg.get("commitIdx"):
                    if not self.staged:
                        self.staged = msg.get("payload")
                    self.commit()
                    self.log_follower_rejected_append_entry(self.addr, msg.get("addr"))
        self.append_to_log(f"NO-OP {self.term}")
        return self.term, self.commitIdx

    def restart(self):
        """
        Method to simulate restarting a follower node.
        """
        self.status = FOLLOWER
        self.voteCount = 0
        self.term = 0
        self.commitIdx = 0
        self.init_timeout()

    def init_timeout(self):
        self.reset_timeout()
        if self.timeout_thread:
            if self.timeout_thread.is_alive():
                return
        self.timeout_thread = threading.Thread(target=self.timeout_loop)
        self.timeout_thread.start()

    def timeout_loop(self):
        while self.status != LEADER:
            delta = self.election_time - time.time()
            if delta >= 0:
                time.sleep(delta)
            else:
                self.startElection()
                self.log_error_sending_rpc(self.addr)
                
    def handle_get(self, payload):
        self.dump_logs(f"Node {self.addr} (leader) received a GET request")
        print("getting", payload)
        key = payload.get("key")
        if key is None:
            return None
        if key not in self.DB:
            return None
        else:
            payload["value"] = self.DB[key]
            return payload

    def spread_update(self, message, confirmations=None, lock=None):
        for i, each in enumerate(self.fellow):
            r = utils.send(each, "heartbeat", message)
            if r:
                if confirmations:
                    # CONSIDER COMMENTING
                    print(f" - - {message['action']} by {each}")
                    confirmations[i] = True
        if lock:
            lock.release()

    def handle_put(self, payload):
        if not self.lease_acquisition_allowed:
            self.dump_logs("New leader waiting for old leader lease to timeout.")
            print("Cannot perform operation: Leader lease has not expired and so writes are unavailable at the moment. Please try again later.")
            return False

        self.dump_logs(f"Node {self.addr} (leader) received a PUT request")
        self.lock.acquire()
        print("putting", payload)
        waited = 0
        self.staged = payload
        self.append_to_log(f"SET {payload['key']} {payload['value']} {self.term}")
        log_message = {
            "term": self.term,
            "payload": payload,
            "addr": self.addr,
            "commitIdx": self.commitIdx,
            "action": "log",
        }
        log_confirmations = [False] * len(self.fellow)
        threading.Thread(target=self.spread_update, args=(log_message, log_confirmations)).start()
        while self.majority - 1 > sum(log_confirmations):
            waited += 0.0005
            time.sleep(0.0005)
            max_wait = cfg.MAX_LOG_WAIT / 1000
            if waited > max_wait:
                print(f"waited {cfg.MAX_LOG_WAIT} ms, update rejected:")
                self.dump_logs(f"Waited {cfg.MAX_LOG_WAIT} ms, update rejected:")
                self.lock.release()
                return False
        commit_message = {
            "term": self.term,
            "payload": payload,
            "addr": self.addr,
            "commitIdx": self.commitIdx,
            "action": "commit",
        }
        self.commit()
        threading.Thread(target=self.spread_update, args=(commit_message, None, self.lock)).start()
        print("majority reached, replied to client, sending message to commit")
        self.dump_logs("Majority reached, replied to client, sending message to commit")
        if payload["value"]:
            # self.append_to_log(f"SET {payload['key']} {payload['value']} {self.term}")
            self.log_leader_received_request(self.addr, f"SET {payload['key']} {payload['value']} {self.term}")
        return True

    def commit(self):
        self.commitIdx += 1
        value = self.staged["value"]
        key = self.staged["key"]
        self.log.append(self.staged)
        self.staged = None
        self.DB[key] = value
        self.log_follower_commit(self.addr, f"SET {key} {value} {self.term}")

    def vote_granted(self, candidate_node_id, term):
        self.dump_logs(f"Vote granted for Node {candidate_node_id} in term {term}.")

    def vote_denied(self, candidate_node_id, term):
        self.dump_logs(f"Vote denied for Node {candidate_node_id} in term {term}.")

    def log_error_sending_rpc(self, followerNodeID):
        message = f"Error occurred while sending RPC to Node {followerNodeID}."
        self.dump_logs(message)

    def log_follower_commit(self, followerNodeID, entry_operation):
        message = f"Node {followerNodeID} (follower) committed the entry {entry_operation} to the state machine."
        self.dump_logs(message)

    def log_leader_received_request(self, leaderNodeID, entry_operation):
        message = f"Node {leaderNodeID} (leader) received an {entry_operation} request."
        self.dump_logs(message)

    def log_leader_commit(self, leaderNodeID, entry_operation):
        message = f"Node {leaderNodeID} (leader) committed the entry {entry_operation} to the state machine."
        self.dump_logs(message)

    def log_follower_accepted_append_entry(self, followerNodeID, leaderNodeID):
        message = f"Node {followerNodeID} accepted AppendEntries RPC from {leaderNodeID}."
        self.dump_logs(message)

    def log_follower_rejected_append_entry(self, followerNodeID, leaderNodeID):
        message = f"Node {followerNodeID} rejected AppendEntries RPC from {leaderNodeID}."
        self.dump_logs(message)

    def log_vote_granted(self, candidateNodeID, term):
        message = f"Vote granted for Node {candidateNodeID} in term {term}."
        self.dump_logs(message)

    def log_vote_denied(self, candidateNodeID, term):
        message = f"Vote denied for Node {candidateNodeID} in term {term}."
        self.dump_logs(message)

    def log_leader_stepping_down(self, nodeID):
        message = f"{nodeID} Stepping down"
        self.dump_logs(message)
