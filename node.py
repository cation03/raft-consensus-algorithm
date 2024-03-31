# import threading
# import time
# import utils
# from config import cfg
# import grpc
# import server_pb2
# import server_pb2_grpc

# FOLLOWER = 0
# CANDIDATE = 1
# LEADER = 2


# class Node():
#     def __init__(self, fellow, my_ip):
#         self.addr = my_ip
#         self.fellow = fellow
#         self.lock = threading.Lock()
#         self.DB = {}
#         self.log = []
#         self.staged = None
#         self.term = 0
#         self.status = FOLLOWER
#         self.majority = ((len(self.fellow) + 1) // 2) + 1
#         self.voteCount = 0
#         self.commitIdx = 0
#         self.timeout_thread = None
#         self.lease_timer = None  # Lease timer
#         self.lease_acquisition_allowed = True  # Flag to indicate if lease acquisition is allowed
#         self.init_timeout()


#     # increment only when we are candidate and receive positve vote
#     # change status to LEADER and start heartbeat as soon as we reach majority
#     def incrementVote(self):
#         self.voteCount += 1
#         if self.voteCount >= self.majority:
#             print(f"{self.addr} becomes the leader of term {self.term}")
#             self.status = LEADER
#             self.startHeartBeat()

#     # vote for myself, increase term, change status to candidate
#     # reset the timeout and start sending request to followers
#     def startElection(self):
#         if self.lease_acquisition_allowed:
#             self.term += 1
#             self.voteCount = 0
#             self.status = CANDIDATE
#             self.init_timeout()
#             self.incrementVote()
#             self.send_vote_req()
#         else:
#             print("Cannot start election: Leader lease has not expired.")


#     # ------------------------------
#     # ELECTION TIME CANDIDATE

#     # spawn threads to request vote for all followers until get reply
#     def send_vote_req(self):
#         # TODO: use map later for better performance
#         # we continue to ask to vote to the address that haven't voted yet
#         # till everyone has voted
#         # or I am the leader
#         for voter in self.fellow:
#             threading.Thread(target=self.ask_for_vote,
#                              args=(voter, self.term)).start()

#     # request vote to other servers during given election term
#     def ask_for_vote(self, voter, term):
#         # need to include self.commitIdx, only up-to-date candidate could win
#         message = {
#             "term": term,
#             "commitIdx": self.commitIdx,
#             "staged": self.staged
#         }
#         route = "vote_req"
#         while self.status == CANDIDATE and self.term == term:
#             reply = utils.send(voter, route, message)
#             if reply:
#                 choice = reply.json()["choice"]
#                 # print(f"RECEIVED VOTE {choice} from {voter}")
#                 if choice and self.status == CANDIDATE:
#                     self.incrementVote()
#                 elif not choice:
#                     # they declined because either I'm out-of-date or not newest term
#                     # update my term and terminate the vote_req
#                     term = reply.json()["term"]
#                     if term > self.term:
#                         self.term = term
#                         self.status = FOLLOWER
#                     # fix out-of-date needed
#                 break

#     # ------------------------------
#     # ELECTION TIME FOLLOWER

#     # some other server is asking
#     def decide_vote(self, term, commitIdx, staged):
#         # new election
#         # decline all non-up-to-date candidate's vote request as well
#         # but update term all the time, not reset timeout during decision
#         # also vote for someone that has our staged version or a more updated one
#         if self.term < term and self.commitIdx <= commitIdx and (
#                 staged or (self.staged == staged)):
#             self.reset_timeout()
#             self.term = term
#             return True, self.term
#         else:
#             return False, self.term

#     # ------------------------------
#     # START PRESIDENT

#     def startHeartBeat(self):
#         print("Starting HEARTBEAT")
#         if self.staged:
#             # we have something staged at the beginning of our leadership
#             # we consider it as a new payload just received and spread it around
#             self.handle_put(self.staged)

#         if self.lease_acquisition_allowed:
#             # Start the lease timer only if lease acquisition is allowed
#             self.start_lease_timer()

#             # Replicate the lease interval to followers
#             self.replicate_lease_interval()

#         for each in self.fellow:
#             t = threading.Thread(target=self.send_heartbeat, args=(each,))
#             t.start()


#     def start_lease_timer(self):
#         # Start the lease timer
#         self.lease_timer = threading.Timer(cfg.LEASE_INTERVAL, self.renew_lease)
#         self.lease_timer.start()

#     def renew_lease(self):
#         # This function will be called when the lease interval expires
#         print(f"Lease interval expired for leader {self.addr}. Renewing lease.")
#         # Allow lease acquisition for new leader
#         self.lease_acquisition_allowed = True
#         if self.status == LEADER:
#             self.status = FOLLOWER
#             self.init_timeout()
#             print(f"Leader {self.addr} has stepped down. Starting election.")
#             self.startElection()


#     def replicate_lease_interval(self):
#         # Replicate the lease interval to followers
#         for follower in self.fellow:
#             threading.Thread(target=self.send_lease_interval, args=(follower,)).start()

#     def send_lease_interval(self, follower):
#         # Send the lease interval to a follower
#         route = "lease_interval"
#         message = {"interval": cfg.LEASE_INTERVAL}
#         utils.send(follower, route, message)


#     def update_follower_commitIdx(self, follower):
#         route = "heartbeat"
#         first_message = {"term": self.term, "addr": self.addr}
#         second_message = {
#             "term": self.term,
#             "addr": self.addr,
#             "action": "commit",
#             "payload": self.log[-1]
#         }
#         reply = utils.send(follower, route, first_message)
#         if reply and reply.json()["commitIdx"] < self.commitIdx:
#             # they are behind one commit, send follower the commit:
#             reply = utils.send(follower, route, second_message)

#     def send_heartbeat(self, follower):
#         # check if the new follower have same commit index, else we tell them to update to our log level
#         if self.log:
#             self.update_follower_commitIdx(follower)

#         route = "heartbeat"
#         message = {"term": self.term, "addr": self.addr}
#         while self.status == LEADER:
#             start = time.time()
#             reply = utils.send(follower, route, message)
#             if reply:
#                 self.heartbeat_reply_handler(reply.json()["term"],
#                                              reply.json()["commitIdx"])
#             delta = time.time() - start
#             # keep the heartbeat constant even if the network speed is varying
#             time.sleep((cfg.HB_TIME - delta) / 1000)

#     # we may step down when get replied
#     def heartbeat_reply_handler(self, term, commitIdx):
#         # i thought i was leader, but a follower told me
#         # that there is a new term, so i now step down
#         if term > self.term:
#             self.term = term
#             self.status = FOLLOWER
#             self.init_timeout()

#         # TODO logging replies

#     # ------------------------------
#     # FOLLOWER STUFF

#     def reset_timeout(self):
#         self.election_time = time.time() + utils.random_timeout()

#     # /heartbeat

#     def heartbeat_follower(self, msg):
#         # weird case if 2 are PRESIDENT of same term.
#         # both receive an heartbeat
#         # we will both step down
#         # term = msg["term"]
#         term = msg.get("term")
#         if self.term <= term:
#             # self.leader = msg["addr"]
#             self.leader = msg.get("addr")
#             self.reset_timeout()
#             # in case I am not follower
#             # or started an election and lost it
#             if self.status == CANDIDATE:
#                 self.status = FOLLOWER
#             elif self.status == LEADER:
#                 self.status = FOLLOWER
#                 self.init_timeout()
#             # i have missed a few messages
#             if self.term < term:
#                 self.term = term

#             # handle client request
#             if "action" in msg:
#                 print("received action", msg)
#                 # action = msg["action"]
#                 action = msg.get("action")
#                 # logging after first msg
#                 if action == "log":
#                     # payload = msg["payload"]
#                     payload = msg.get("payload")
#                     self.staged = payload
#                 # proceeding staged transaction
#                 # elif self.commitIdx <= msg["commitIdx"]:
                
#                 elif msg.get("commitIdx") is not None and self.commitIdx <= msg.get("commitIdx"):
#                     if not self.staged:
#                         # self.staged = msg["payload"]
#                         self.staged = msg.get("payload")
#                     self.commit()

#         return self.term, self.commitIdx

#     def restart(self):
#         """
#         Method to simulate restarting a follower node.
#         """
#         self.status = FOLLOWER
#         self.voteCount = 0
#         self.term = 0
#         self.commitIdx = 0
#         self.init_timeout()


#     # initiate timeout thread, or reset it
#     def init_timeout(self):
#         self.reset_timeout()
#         # safety guarantee, timeout thread may expire after election
#         if self.timeout_thread and self.timeout_thread.is_alive():
#             return
#         self.timeout_thread = threading.Thread(target=self.timeout_loop)
#         self.timeout_thread.start()

#     # the timeout function
#     def timeout_loop(self):
#         # only stop timeout thread when winning the election
#         while self.status != LEADER:
#             delta = self.election_time - time.time()
#             if delta < 0:
#                 self.startElection()
#             else:
#                 time.sleep(delta)

#     def handle_get(self, payload):
#         print("getting", payload)
#         # key = payload["key"]
#         key = payload.get("key")
#         if key is None:
#             return None
#         if key in self.DB:
#             payload["value"] = self.DB[key]
#             return payload
#         else:
#             return None

#     # takes a message and an array of confirmations and spreads it to the followers
#     # if it is a comit it releases the lock
#     def spread_update(self, message, confirmations=None, lock=None):
#         for i, each in enumerate(self.fellow):
#             r = utils.send(each, "heartbeat", message)
#             if r and confirmations:
#                 # print(f" - - {message['action']} by {each}")
#                 confirmations[i] = True
#         if lock:
#             lock.release()

#     def handle_put(self, payload):
#         if not self.lease_acquisition_allowed:
#             print("Cannot perform operation: Leader lease has not expired and so writes are unavailable at the moment. Please try again later.")
#             return False

#         print("putting", payload)

#         # lock to only handle one request at a time
#         self.lock.acquire()
#         self.staged = payload
#         waited = 0
#         log_message = {
#             "term": self.term,
#             "addr": self.addr,
#             "payload": payload,
#             "action": "log",
#             "commitIdx": self.commitIdx
#         }

#         # spread log to everyone
#         log_confirmations = [False] * len(self.fellow)
#         threading.Thread(target=self.spread_update,
#                          args=(log_message, log_confirmations)).start()
#         while sum(log_confirmations) + 1 < self.majority:
#             waited += 0.0005
#             time.sleep(0.0005)
#             if waited > cfg.MAX_LOG_WAIT / 1000:
#                 print(f"waited {cfg.MAX_LOG_WAIT} ms, update rejected:")
#                 self.lock.release()
#                 return False
#         # reach this point only if a majority has replied and tell everyone to commit
#         commit_message = {
#             "term": self.term,
#             "addr": self.addr,
#             "payload": payload,
#             "action": "commit",
#             "commitIdx": self.commitIdx
#         }
#         self.commit()
#         threading.Thread(target=self.spread_update,
#                          args=(commit_message, None, self.lock)).start()
#         print("majority reached, replied to client, sending message to commit")
#         return True
#         # print("putting", payload)

#         # # lock to only handle one request at a time
#         # self.lock.acquire()
#         # self.staged = payload
#         # waited = 0
#         # log_message = {
#         #     "term": self.term,
#         #     "addr": self.addr,
#         #     "payload": payload,
#         #     "action": "log",
#         #     "commitIdx": self.commitIdx
#         # }

#         # # spread log  to everyone
#         # log_confirmations = [False] * len(self.fellow)
#         # threading.Thread(target=self.spread_update,
#         #                  args=(log_message, log_confirmations)).start()
#         # while sum(log_confirmations) + 1 < self.majority:
#         #     waited += 0.0005
#         #     time.sleep(0.0005)
#         #     if waited > cfg.MAX_LOG_WAIT / 1000:
#         #         print(f"waited {cfg.MAX_LOG_WAIT} ms, update rejected:")
#         #         self.lock.release()
#         #         return False
#         # # reach this point only if a majority has replied and tell everyone to commit
#         # commit_message = {
#         #     "term": self.term,
#         #     "addr": self.addr,
#         #     "payload": payload,
#         #     "action": "commit",
#         #     "commitIdx": self.commitIdx
#         # }
#         # self.commit()
#         # threading.Thread(target=self.spread_update,
#         #                  args=(commit_message, None, self.lock)).start()
#         # print("majority reached, replied to client, sending message to commit")
#         # return True

#     # put staged key-value pair into local database
#     def commit(self):
#         self.commitIdx += 1
#         self.log.append(self.staged)
#         key = self.staged["key"]
#         value = self.staged["value"]
#         self.DB[key] = value
#         # empty the staged so we can vote accordingly if there is a tie
#         self.staged = None

# import threading
# import time
# import utils
# from config import cfg

# FOLLOWER = 0
# CANDIDATE = 1
# LEADER = 2


# class Node():
#     def __init__(self, fellow, my_ip):
#         self.addr = my_ip
#         self.fellow = fellow
#         self.lock = threading.Lock()
#         self.DB = {}
#         self.log = []
#         self.staged = None
#         self.term = 0
#         self.status = FOLLOWER
#         self.majority = ((len(self.fellow) + 1) // 2) + 1
#         self.voteCount = 0
#         self.commitIdx = 0
#         self.timeout_thread = None
#         self.lease_timer = None  # Lease timer
#         self.lease_acquisition_allowed = True  # Flag to indicate if lease acquisition is allowed
#         self.init_timeout()

#     # Increment only when we are a candidate and receive a positive vote
#     # Change status to LEADER and start heartbeat as soon as we reach a majority
#     def incrementVote(self):
#         self.voteCount += 1
#         if self.voteCount >= self.majority:
#             print(f"{self.addr} becomes the leader of term {self.term}")
#             self.status = LEADER
#             self.startHeartBeat()

#     # Vote for myself, increase term, change status to candidate
#     # Reset the timeout and start sending requests to followers
#     def startElection(self):
#         if self.lease_acquisition_allowed:
#             self.term += 1
#             self.voteCount = 0
#             self.status = CANDIDATE
#             self.init_timeout()
#             self.incrementVote()
#             self.send_vote_req()
#         else:
#             print("Cannot start election: Leader lease has not expired.")

#     # Spawn threads to request votes from all followers until we get a reply
#     def send_vote_req(self):
#         for voter in self.fellow:
#             threading.Thread(target=self.ask_for_vote,
#                              args=(voter, self.term)).start()

#     # Request votes from other servers during the given election term
#     def ask_for_vote(self, voter, term):
#         message = {
#             "term": term,
#             "commitIdx": self.commitIdx,
#             "staged": self.staged
#         }
#         route = "vote_req"
#         while self.status == CANDIDATE and self.term == term:
#             reply = utils.send(voter, route, message)
#             if reply:
#                 choice = reply.json()["choice"]
#                 if choice and self.status == CANDIDATE:
#                     self.incrementVote()
#                 elif not choice:
#                     term = reply.json()["term"]
#                     if term > self.term:
#                         self.term = term
#                         self.status = FOLLOWER
#                 break

#     # Decide whether to vote for a candidate or not
#     def decide_vote(self, term, commitIdx, staged):
#         if self.term < term and self.commitIdx <= commitIdx and (
#                 staged or (self.staged == staged)):
#             self.reset_timeout()
#             self.term = term
#             return True, self.term
#         else:
#             return False, self.term

#     # Start heartbeat when becoming leader
#     def startHeartBeat(self):
#         print("Starting HEARTBEAT")
#         if self.staged:
#             self.handle_put(self.staged)

#         if self.lease_acquisition_allowed:
#             self.start_lease_timer()
#             self.replicate_lease_interval()

#         for each in self.fellow:
#             t = threading.Thread(target=self.send_heartbeat, args=(each,))
#             t.start()

#     # Start the lease timer
#     def start_lease_timer(self):
#         self.lease_timer = threading.Timer(cfg.LEASE_INTERVAL, self.renew_lease)
#         self.lease_timer.start()

#     # Function to renew lease after it expires
#     def renew_lease(self):
#         print(f"Lease interval expired for leader {self.addr}. Renewing lease.")
#         self.lease_acquisition_allowed = True
#         if self.status == LEADER:
#             self.status = FOLLOWER
#             self.init_timeout()
#             print(f"Leader {self.addr} has stepped down. Starting election.")
#             self.startElection()

#     # Replicate the lease interval to followers
#     def replicate_lease_interval(self):
#         for follower in self.fellow:
#             threading.Thread(target=self.send_lease_interval, args=(follower,)).start()

#     # Send the lease interval to a follower
#     def send_lease_interval(self, follower):
#         route = "lease_interval"
#         message = {"interval": cfg.LEASE_INTERVAL}
#         utils.send(follower, route, message)

#     # Update follower's commit index
#     def update_follower_commitIdx(self, follower):
#         route = "heartbeat"
#         first_message = {"term": self.term, "addr": self.addr}
#         second_message = {
#             "term": self.term,
#             "addr": self.addr,
#             "action": "commit",
#             "payload": self.log[-1]
#         }
#         reply = utils.send(follower, route, first_message)
#         if reply and reply.json()["commitIdx"] < self.commitIdx:
#             reply = utils.send(follower, route, second_message)

#     # Send heartbeat to followers
#     def send_heartbeat(self, follower):
#         if self.log:
#             self.update_follower_commitIdx(follower)

#         route = "heartbeat"
#         message = {"term": self.term, "addr": self.addr}
#         while self.status == LEADER:
#             start = time.time()
#             reply = utils.send(follower, route, message)
#             if reply:
#                 self.heartbeat_reply_handler(reply.json()["term"],
#                                              reply.json()["commitIdx"])
#             delta = time.time() - start
#             time.sleep((cfg.HB_TIME - delta) / 1000)

#     # Handle heartbeat replies
#     def heartbeat_reply_handler(self, term, commitIdx):
#         if term > self.term:
#             self.term = term
#             self.status = FOLLOWER
#             self.init_timeout()

#     # Reset the election timeout
#     def reset_timeout(self):
#         self.election_time = time.time() + utils.random_timeout()

#     # Handle heartbeat from followers
#     def heartbeat_follower(self, msg):
#         term = msg.get("term")
#         if self.term <= term:
#             self.leader = msg.get("addr")
#             self.reset_timeout()
#             if self.status == CANDIDATE:
#                 self.status = FOLLOWER
#             elif self.status == LEADER:
#                 self.status = FOLLOWER
#                 self.init_timeout()
#             if self.term < term:
#                 self.term = term

#             if "action" in msg:
#                 action = msg.get("action")
#                 if action == "log":
#                     payload = msg.get("payload")
#                     self.staged = payload
#                 elif msg.get("commitIdx") is not None and self.commitIdx <= msg.get("commitIdx"):
#                     if not self.staged:
#                         self.staged = msg.get("payload")
#                     self.commit()

#         return self.term, self.commitIdx

#     # Restart the node (simulate a follower restarting)
#     def restart(self):
#         self.status = FOLLOWER
#         self.voteCount = 0
#         self.term = 0
#         self.commitIdx = 0
#         self.init_timeout()

#     # Initialize timeout thread
#     def init_timeout(self):
#         self.reset_timeout()
#         if self.timeout_thread and self.timeout_thread.is_alive():
#             return
#         self.timeout_thread = threading.Thread(target=self.timeout_loop)
#         self.timeout_thread.start()

#     # Timeout loop function
#     def timeout_loop(self):
#         while self.status != LEADER:
#             delta = self.election_time - time.time()
#             if delta < 0:
#                 self.startElection()
#             else:
#                 time.sleep(delta)

#     # Handle GET requests
#     def handle_get(self, payload):
#         key = payload.get("key")
#         if key is None:
#             return None
#         if key in self.DB:
#             payload["value"] = self.DB[key]
#             return payload
#         else:
#             return None

#     # Spread updates to followers
#     def spread_update(self, message, confirmations=None, lock=None):
#         for i, each in enumerate(self.fellow):
#             r = utils.send(each, "heartbeat", message)
#             if r and confirmations:
#                 confirmations[i] = True
#         if lock:
#             lock.release()

#     # Handle PUT requests
#     def handle_put(self, payload):
#         if not self.lease_acquisition_allowed:
#             print("Cannot perform operation: Leader lease has not expired and so writes are unavailable at the moment. Please try again later.")
#             return False

#         self.lock.acquire()
#         self.staged = payload
#         waited = 0
#         log_message = {
#             "term": self.term,
#             "addr": self.addr,
#             "payload": payload,
#             "action": "log",
#             "commitIdx": self.commitIdx
#         }

#         log_confirmations = [False] * len(self.fellow)
#         threading.Thread(target=self.spread_update,
#                          args=(log_message, log_confirmations)).start()
#         while sum(log_confirmations) + 1 < self.majority:
#             waited += 0.0005
#             time.sleep(0.0005)
#             if waited > cfg.MAX_LOG_WAIT / 1000:
#                 print(f"Waited {cfg.MAX_LOG_WAIT} ms, update rejected:")
#                 self.lock.release()
#                 return False

#         commit_message = {
#             "term": self.term,
#             "addr": self.addr,
#             "payload": payload,
#             "action": "commit",
#             "commitIdx": self.commitIdx
#         }
#         self.commit()
#         threading.Thread(target=self.spread_update,
#                          args=(commit_message, None, self.lock)).start()
#         print("Majority reached, replied to client, sending message to commit")
#         return True

#     # Commit staged key-value pair into the local database
#     def commit(self):
#         self.commitIdx += 1
#         self.log.append(self.staged)
#         key = self.staged["key"]
#         value = self.staged["value"]
#         self.DB[key] = value
#         self.staged = None
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
        # Dump initial message
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

    # increment only when we are candidate and receive positive vote
    # change status to LEADER and start heartbeat as soon as we reach majority
    def incrementVote(self):
        self.voteCount += 1
        self.append_metadata(f"{self.commitIdx} {self.term} {self.node_id}")
        if self.voteCount >= self.majority:
            self.status = LEADER
            self.startHeartBeat()
            # self.append_metadata(f"{self.commitIdx} {self.term} {self.addr}")
            self.dump_logs(f"Node {self.addr} became the leader for term {self.term}")
            print(f"{self.addr} becomes the leader of term {self.term}")
        else:
            print(f"{self.node_id} voted for {self.addr} in term {self.term}")
            # self.append_metadata(f"{self.commitIdx} {self.term} {self.node_id}")

    def startElection(self):
        self.term += 1
        self.voteCount = 0
        self.status = CANDIDATE
        # self.initiate_metadata()  # Reset metadata file for new term
        self.init_timeout()
        self.incrementVote()
        self.send_vote_req()

    def send_vote_req(self):
        for voter in self.fellow:
            threading.Thread(target=self.ask_for_vote, args=(voter, self.term)).start()

    # # request vote to other servers during given election term
    # def ask_for_vote(self, voter, term):
    #     message = {
    #         "term": term,
    #         "commitIdx": self.commitIdx,
    #         "staged": self.staged
    #     }
    #     route = "vote_req"
    #     while self.status == CANDIDATE and self.term == term:
    #         reply = utils.send(voter, route, message)
    #         if reply:
    #             choice = reply.json()["choice"]
    #             print("RECEIVED VOTE", choice, "from", voter)
    #             if choice and self.status == CANDIDATE:
    #                 self.incrementVote()
    #             elif not choice:
    #                 term = reply.json()["term"]
    #                 if term > self.term:
    #                     self.term = term
    #                     self.status = FOLLOWER
    #             break
            
    def ask_for_vote(self, voter, term):
        message = {
            "term": term,
            "commitIdx": self.commitIdx,
            "staged": self.staged
        }
        route = "vote_req"
        voter_id = self.node_id
        while self.status == CANDIDATE and self.term == term:
            reply = utils.send(voter, route, message)
            if reply:
                choice = reply.json()["choice"]
                voter_id = int(str(voter)[-1])  # Extract voter's node ID from its IP address
                if choice:
                    self.incrementVote()
                    # vote_info = f"Voted for Node {voter_id} in term {term}, commitIdx {self.commitIdx}"
                    # print(vote_info)
                    # self.append_to_log(vote_info)  # Add vote information to the logs
                    # Append metadata indicating the voted node's ID
                elif not choice:
                    term = reply.json()["term"]
                    if term > self.term:
                        self.term = term
                        self.status = FOLLOWER
                        # self.append_to_log(f"Received higher term {term}, converting to follower")
                        break
            break
        self.append_metadata(f"{self.commitIdx} {term} {voter_id}")

    # some other server is asking
    def decide_vote(self, term, commitIdx, staged):
        if self.term < term and self.commitIdx <= commitIdx and (
                staged or (self.staged == staged)):
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

        if self.lease_acquisition_allowed == True:
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
            self.dump_logs(f"{self.addr} Stepping down")
            print(f"Leader {self.addr} has stepped down. Starting election.")
            self.startElection()

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
            "addr": self.addr,
            "action": "commit",
            "payload": self.log[-1]
        }
        route = "heartbeat"
        
        reply = utils.send(follower, route, first_message)
        
        if reply != None:
            if reply.json()["commitIdx"] < self.commitIdx:
                reply = utils.send(follower, route, second_message)

    def send_heartbeat(self, follower):
        if self.log:
            self.update_follower_commitIdx(follower)

        message = {"term": self.term, "addr": self.addr}
        route = "heartbeat"
        while self.status == LEADER:
            start = time.time()
            reply = utils.send(follower, route, message)
            if reply:
                self.heartbeat_reply_handler(reply.json()["term"],
                                             reply.json()["commitIdx"])
            curr_time = time.time()
            delta = curr_time - start
            diff = cfg.HB_TIME - delta
            time.sleep(diff / 1000)

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
            if self.term < term:
                self.term = term

            if "action" in msg:
                self.dump_logs(f"Node {self.addr} (follower) received an {msg['action']} request")
                print("received action", msg)
                # append to log only if action is commit
                if msg["action"] == "commit":
                    self.append_to_log(f"SET {msg['payload']['key']} {msg['payload']['value']} {self.term}")
                if msg["action"] == "log":
                    self.staged = msg.get("payload")
                elif msg.get("commitIdx") is not None and self.commitIdx <= msg.get("commitIdx"):
                    if not self.staged:
                        self.staged = msg.get("payload")
                    self.commit()

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
            print("Cannot perform operation: Leader lease has not expired and so writes are unavailable at the moment. Please try again later.")
            return False

        self.dump_logs(f"Node {self.addr} (leader) received a PUT request")
        self.lock.acquire()
        print("putting", payload)
        waited = 0
        self.staged = payload
        log_message = {
            "term": self.term,
            "addr": self.addr,
            "payload": payload,
            "action": "log",
            "commitIdx": self.commitIdx
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
            "addr": self.addr,
            "payload": payload,
            "action": "commit",
            "commitIdx": self.commitIdx
        }
        self.commit()
        threading.Thread(target=self.spread_update, args=(commit_message, None, self.lock)).start()
        print("majority reached, replied to client, sending message to commit")
        self.dump_logs("Majority reached, replied to client, sending message to commit")
        self.append_to_log(f"SET {payload['key']} {payload['value']} {self.term}")
        return True

    def commit(self):
        self.commitIdx += 1
        self.log.append(self.staged)
        value = self.staged["value"]
        key = self.staged["key"]
        self.DB[key] = value
        self.staged = None

    def vote_granted(self, candidate_node_id, term):
        self.dump_logs(f"Vote granted for Node {candidate_node_id} in term {term}.")

    def vote_denied(self, candidate_node_id, term):
        self.dump_logs(f"Vote denied for Node {candidate_node_id} in term {term}.")
