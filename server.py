import sys
import server_pb2 as pb2
import server_pb2_grpc as pb2_grpc
import grpc
import threading, time
from threading import Thread
import random
import math
from concurrent import futures

# Config file has servers addresses that'll be stored in servers.
CONFIG_PATH = "config.conf"  # overwrite this with your config file path
SERVERS = {}

# Server identifying variables.
TERM, VOTED, STATE, VOTES = 0, False, "Follower", 0
LEADER_ID = None
IN_ELECTIONS = False
SERVER_ID = int(sys.argv[1])
VOTED_NODE = -1
SERVER_ACTIVE = True
# Time limit in seconds for timouts, and timer to set the time limit for certain functionalities.
TIME_LIMIT = (random.randrange(150, 301) / 100)
LATEST_TIMER = -1
LEADER_LEASE_DURATION = 5000
# Threads used to request votes from servers as a candidate, and to append entries as a leader.
CANDIDATE_THREADS = []
LEADER_THREADS = []

# Commit Index is index of last log entry on server
# Last applied is index of last applied log entry on server
commitIndex, lastApplied, lastLogTerm = 0, 0, 0
# For applied commits.
ENTRIES = {}
# For non-applied commits.
LOGS = []
LEADER_LEASE_EXPIRATION = None

# NextIndex: list of indices of next log entry to send to server
# MatchIndex: list of indices of latest log entry known to be on every server
nextIndex, matchIndex = [], []
matchTerm = []
n_logs_replicated = 1


class RaftHandler(pb2_grpc.RaftServiceServicer):

    def RequestVote(self, request, context):
        global TERM, VOTED, STATE, VOTED_NODE, IN_ELECTIONS, LATEST_TIMER
        global commitIndex, lastLogTerm
        candidate_term, candidate_id = request.term, request.candidateId
        candidateLastLogIndex, candidateLastLogTerm = request.lastLogIndex, request.lastLogTerm

        IN_ELECTIONS = True
        if TERM < candidate_term:
            TERM = candidate_term
            VOTED = True
            VOTED_NODE = None
            print(f"Did not vote for {candidate_id}.")
            run_follower()
        if len(LOGS) > 0:
            lastLogTerm = LOGS[-1]["TERM"]
        logOk = (candidateLastLogTerm > lastLogTerm) or (candidateLastLogTerm == lastLogTerm and candidateLastLogIndex >= len(LOGS))
        if TERM == candidate_term and logOk and (VOTED_NODE == None or VOTED_NODE == candidate_id): 
            VOTED_NODE = candidate_id
            VOTED = True
            print(f"Voted for node {candidate_id}.")
            reset_timer(leader_died, TIME_LIMIT)
        else:
            if STATE == "Follower":
                reset_timer(leader_died, TIME_LIMIT)

        reply = {"term": TERM, "result": VOTED}
        return pb2.RequestVoteResponse(**reply)

    # This function is used by leader to append entries in followers.
    def AppendEntries(self, request, context):
        global TERM, STATE, LEADER_ID, VOTED, VOTED_NODE
        global LATEST_TIMER, commitIndex, ENTRIES, lastApplied

        leader_term, leader_id = request.term, request.leaderId
        prevLogIndex, prevLogTerm = request.prevLogIndex, request.prevLogTerm
        entries, leaderCommit = request.entries, request.leaderCommit
        result = False
        if leader_term >= TERM:
            # Leader is already in a different term than mine.
            if leader_term > TERM:
                VOTED = False
                VOTED_NODE = -1
                TERM = leader_term
                LEADER_ID = leader_id
                run_follower()

            if prevLogIndex <= len(LOGS):
                result = True
                if len(entries) > 0:
                    LOGS.append({"TERM": leader_term, "ENTRY": entries[0]})

                if leaderCommit > commitIndex:
                    commitIndex = min(leaderCommit, len(LOGS))
                    while commitIndex > lastApplied:
                        key, value = LOGS[lastApplied]["ENTRY"]["key"], LOGS[lastApplied]["ENTRY"]["value"]
                        ENTRIES[key] = value
                        lastApplied += 1


            reset_timer(leader_died, TIME_LIMIT)
        reply = {"term": TERM, "result": result}
        return pb2.AppendEntriesResponse(**reply)

    # This function is called from the client to get leader.
    def GetLeader(self, request, context):
        global IN_ELECTIONS, VOTED, VOTED_NODE, LEADER_ID
        print("Command from client: getleader")
        if IN_ELECTIONS and not VOTED:
            print("None None")
            return pb2.GetLeaderResponse(**{"leaderId": -1, "leaderAddress": "-1"})

        if IN_ELECTIONS:
            print(f"{VOTED_NODE} {SERVERS[VOTED_NODE]}")
            return pb2.GetLeaderResponse(**{"leaderId": VOTED_NODE, "leaderAddress": SERVERS[VOTED_NODE]})

        return pb2.GetLeaderResponse(**{"leaderId": LEADER_ID, "leaderAddress": SERVERS[LEADER_ID]})

    # This function is called from client to suspend server for PERIOD seconds.
    def Suspend(self, request, context):
        global SERVER_ACTIVE
        SUSPEND_PERIOD = int(request.period)
        print(f"Command from client: suspend {SUSPEND_PERIOD}")
        print(f"Sleeping for {SUSPEND_PERIOD} seconds")
        SERVER_ACTIVE = False
        time.sleep(SUSPEND_PERIOD)
        reset_timer(run_server_role(), SUSPEND_PERIOD)
        return pb2.SuspendResponse(**{})

    def SetVal(self, request, context):
        key, val = request.key, request.value
        global STATE, SERVERS, LEADER_ID, LOGS, TERM
        if STATE != "Leader":
            return pb2.SetValResponse(success=False)
        
        try:
            LOGS.append({"TERM": TERM, "ENTRY": {"commandType": "set", "key": key, "value": val}})
            return pb2.SetValResponse(success=True)
        except Exception as e:
            # Log the exception for debugging purposes
            print(f"Error in SetVal: {e}")
            return pb2.SetValResponse(success=False)


    def GetVal(self, request, context):
        key = request.key
        global ENTRIES, STATE, LEADER_ID, SERVERS
        if STATE == "Leader":
            # If this server is the leader, directly retrieve the value
            if key in ENTRIES:
                val = ENTRIES[key]
                return pb2.GetValResponse(success=True, value=val)
            else:
                return pb2.GetValResponse(success=False)
        else:
            # If this server is not the leader, redirect the client to the leader
            try:
                leader_address = SERVERS[LEADER_ID]
                channel = grpc.insecure_channel(leader_address)
                stub = pb2_grpc.RaftServiceStub(channel)
                request = pb2.GetValMessage(key=key)
                response = stub.GetVal(request)
                return response
            except grpc.RpcError as e:
                # Log the error and return failure
                print(f"Error in GetVal: {e}")
                return pb2.GetValResponse(success=False)


    
        # Implement RenewLeaderLease RPC function
    def RenewLeaderLease(self, request, context):
        global LEADER_LEASE_EXPIRATION, LEADER_ID, LEADER_LEASE_DURATION
        if request.leaderId == LEADER_ID:
            # Renew leader lease by updating the expiration time
            lease_duration_ms = request.leaseDuration
            LEADER_LEASE_EXPIRATION = time.time() + (lease_duration_ms / 1000)
            return pb2.RenewLeaderLeaseResponse(success=True)
        else:
            return pb2.RenewLeaderLeaseResponse(success=False)

# Check leader lease expiration periodically
def check_leader_lease():
    global LEADER_LEASE_EXPIRATION, LEADER_LEASE_DURATION
    while True:
        if LEADER_LEASE_EXPIRATION is not None and time.time() > LEADER_LEASE_EXPIRATION:
            print("Leader lease expired. Transitioning to follower.")
            run_follower()
            break
        time.sleep(1)  # Check every second


# Read config file to make the list of servers IDs and addresses.
def read_config(path):
    global SERVERS
    with open(path) as configFile:
        lines = configFile.readlines()
        for line in lines:
            parts = line.split()
            SERVERS[int(parts[0])] = (f"{str(parts[1])}:{str(parts[2])}")


def leader_died():
    global STATE
    if STATE != "Follower":
        return
    print("The leader is dead")
    STATE = "Candidate"
    run_candidate()

def run_follower():
    global STATE
    STATE = "Follower"
    print(f"I'm a follower. Term: {TERM}")
    reset_timer(leader_died, TIME_LIMIT)

def get_vote(server):
    global TERM, STATE, TIME_LIMIT, VOTES
    try:
        channel = grpc.insecure_channel(server)
        stub = pb2_grpc.RaftServiceStub(channel)
        request = pb2.RequestVoteMessage(**{"term": TERM, "candidateId": SERVER_ID})
        response = stub.RequestVote(request)
        if response.term > TERM:
            TERM = response.term
            STATE = "Follower"
            TIME_LIMIT = (random.randrange(150, 301) / 1000)
            reset_timer(leader_died, TIME_LIMIT)
        if response.result:
            VOTES += 1
        return response.result
    except grpc.RpcError:
        pass

def process_votes():
    global STATE, LEADER_ID, CANDIDATE_THREADS, TIME_LIMIT, nextIndex, matchIndex
    for thread in CANDIDATE_THREADS:
        thread.join(0)
    print("Votes received")
    if VOTES > len(SERVERS) / 2:
        print(f"I am a leader. Term: {TERM}")
        STATE = "Leader"
        LEADER_ID = SERVER_ID
        # reset_timer(leader_died, TIME_LIMIT)
        nextIndex = [len(LOGS) for i in range(len(SERVERS))]
        matchIndex = [0 for i in range(len(SERVERS))]
        run_leader()
    else:
        STATE = "Follower"
        TIME_LIMIT = (random.randrange(150, 301) / 1000)
        run_follower()

def run_candidate():
    global TERM, STATE, LEADER_ID, LATEST_TIMER, TIME_LIMIT, IN_ELECTIONS, VOTED_NODE
    global SERVER_ID, VOTES, CANDIDATE_THREADS, VOTED
    TERM += 1
    IN_ELECTIONS = True
    VOTED_NODE = SERVER_ID
    CANDIDATE_THREADS = []
    VOTES = 1
    VOTED = True
    print(f"I'm a candidate. Term: {TERM}.\nVoted for node {SERVER_ID}")
    # Requesting votes.
    for key, value in SERVERS.items():
        if SERVER_ID is key:
            continue
        CANDIDATE_THREADS.append(Thread(target=get_vote, kwargs={'server':value}))
    # Check if you won the election and can become a leader.
    for thread in CANDIDATE_THREADS:
        thread.start()
    reset_timer(process_votes, TIME_LIMIT)


def replicate_log(key, server):
    global LOGS, STATE, matchIndex, matchTerm, nextIndex, n_logs_replicated
    leaderCommit = commitIndex
    prevLogIndex = matchIndex[key]
    log=[]
    prevLogTerm = TERM
    if nextIndex[key] < len(LOGS):
        # {"commandType": "set", "key": request.key, "value": request.value}
        log = [{"commandType": "set", "key": LOGS[nextIndex[key]-1]["ENTRY"]["key"], "value": LOGS[nextIndex[key]-1]["ENTRY"]["value"]}]
        prevLogTerm = LOGS[prevLogIndex]["TERM"]
    try:
        channel = grpc.insecure_channel(server)
        stub = pb2_grpc.RaftServiceStub(channel)
        request = pb2.AppendEntriesMessage(**{"term": TERM, "leaderId": SERVER_ID,
                                              "prevLogIndex": prevLogIndex, "prevLogTerm": prevLogTerm,
                                              "entries": log,"leaderCommit": leaderCommit})
        response = stub.AppendEntries(request)
        if(response.term > TERM):
            STATE = "Follower"
            reset_timer(leader_died, TIME_LIMIT)
            run_follower()
        if response.result:
            if log!= []:
                matchIndex[key] = nextIndex[key]
                nextIndex[key] += 1
                n_logs_replicated += 1
        else:
            nextIndex[key] -= 1 
            matchIndex[key] = min(matchIndex[key], nextIndex[key]-1)
    except grpc.RpcError:
        pass

def renew_leader_lease():
    global LEADER_LEASE_EXPIRATION, LEADER_ID, LEADER_LEASE_DURATION
    try:
        channel = grpc.insecure_channel(SERVERS[LEADER_ID])
        stub = pb2_grpc.RaftServiceStub(channel)
        request = pb2.RenewLeaderLeaseRequest(leaderId=SERVER_ID, leaseDuration=LEADER_LEASE_DURATION)
        response = stub.RenewLeaderLease(request)
        if response.success:
            # Renewal successful, update lease expiration time
            LEADER_LEASE_EXPIRATION = time.time() + (LEADER_LEASE_DURATION / 1000)
        else:
            print("Failed to renew leader lease.")
    except grpc.RpcError:
        print("Failed to communicate with leader for lease renewal.")

def run_leader():
    global SERVER_ID, STATE, LEADER_THREADS, n_logs_replicated, nextIndex, lastApplied, commitIndex
    # Renew the leader lease
    if LEADER_ID == SERVER_ID:
        renew_leader_lease()
    # Check leader lease expiration
    if LEADER_LEASE_EXPIRATION is not None and time.time() > LEADER_LEASE_EXPIRATION:
        print("Leader lease expired. Transitioning to follower.")
        run_follower()
        return

    # Send messages after 50 milliseconds.
    LEADER_THREADS = []
    n_logs_replicated = 1
    for key in SERVERS:
        if SERVER_ID is key:
            continue
        LEADER_THREADS.append(Thread(target=replicate_log, kwargs={'key': key, 'server': SERVERS[key]}))
    for thread in LEADER_THREADS:
        thread.start()
    if len(LOGS) > len(ENTRIES):
        key, value = LOGS[lastApplied]["ENTRY"]["key"], LOGS[lastApplied]["ENTRY"]["value"]
        ENTRIES[key] = value
        lastApplied += 1
        commitIndex += 1
    # Reset the timer with the leader lease duration
    reset_timer(run_server_role, LEADER_LEASE_DURATION)

def reset_timer(func, time_limit):
    global LATEST_TIMER
    LATEST_TIMER.cancel()
    LATEST_TIMER = threading.Timer(time_limit, func)
    LATEST_TIMER.start()

def run_server_role():
    global SERVER_ACTIVE
    SERVER_ACTIVE = True
    if(STATE == "Leader"):
        run_leader()
    elif STATE == "Candidate":
        run_candidate()
    else:
        run_follower()

def run_server():
    global TERM, STATE, SERVERS, TIME_LIMIT, LATEST_TIMER
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    pb2_grpc.add_RaftServiceServicer_to_server(RaftHandler(), server)
    server.add_insecure_port(SERVERS[SERVER_ID])
    # print follower start
    print(f"I'm a follower. Term: {TERM}")
    LATEST_TIMER = threading.Timer(TIME_LIMIT, leader_died)
    LATEST_TIMER.start()
    try:
        server.start()
        while (True):
            server.wait_for_termination()
    except KeyboardInterrupt:
        print(f"Server {SERVER_ID} is shutting down")

from node import Node
from node import FOLLOWER, LEADER
from flask import Flask, request, jsonify
import sys
import logging
import os

app = Flask(__name__)


# value_get is the flask handle
@app.route("/request", methods=['GET'])
def value_get():
    payload = request.json["payload"]
    reply = {"code": 'fail', 'payload': payload}
    if n.status == LEADER:
        # request handle, reply is a dictionary
        result = n.handle_get(payload)
        if result:
            reply = {"code": "success", "payload": result}
    elif n.status == FOLLOWER:
        # redirect request
        reply = {"code": "redirect", "message": n.leader, "payload": payload}
    return jsonify(reply)


@app.route("/request", methods=['PUT'])
def value_put():
    payload = request.json["payload"]
    reply = {"code": 'fail'}

    if n.status == LEADER:
        # request handle, reply is a dictionary
        result = n.handle_put(payload)
        if result:
            reply = {"code": "success"}
    elif n.status == FOLLOWER:
        # redirect request
        reply = {"code": "fail", "message": n.leader}
    return jsonify(reply)


# we reply to vote request
@app.route("/vote_req", methods=['POST'])
def vote_req():
    # also need to let me know whether up-to-date or not
    term = request.json["term"]
    commitIdx = request.json["commitIdx"]
    staged = request.json["staged"]
    choice, term = n.decide_vote(term, commitIdx, staged)
    message = {"choice": choice, "term": term}
    return jsonify(message)


@app.route("/heartbeat", methods=['POST'])
def heartbeat():
    term, commitIdx = n.heartbeat_follower(request.json)
    # return anyway, if nothing received by leader, we are dead
    message = {"term": term, "commitIdx": commitIdx}
    return jsonify(message)


# disable flask logging
log = logging.getLogger('werkzeug')
log.disabled = True


if __name__ == "__main__":
    # python server.py index ip_list
    if len(sys.argv) == 3:
        index = int(sys.argv[1])
        ip_list_file = sys.argv[2]
        ip_list = []
        # open ip list file and parse all the ips
        with open(ip_list_file) as f:
            for ip in f:
                ip_list.append(ip.strip())
        my_ip = ip_list.pop(index)

        http, host, port = my_ip.split(':')
        # initialize node with ip list and its own ip
        n = Node(ip_list, my_ip)

        cli = sys.modules['flask.cli']
        cli.show_server_banner = lambda *x: None

        # os.environ['WERKZEUG_RUN_MAIN'] 
        app.run(host="0.0.0.0", port=int(port), debug=False, use_reloader=False, use_debugger=False)
    else:
        print("usage: python server.py <index> <ip_list_file>")


if __name__ == '__main__':
    # Redirect standard output and error streams to /dev/null
    with open(os.devnull, 'w') as f:
        import sys
        sys.stdout = f
        sys.stderr = f
        
        cli = sys.modules['flask.cli']
        cli.show_server_banner = lambda *x: None

        # Run the Flask app
        app.run()
