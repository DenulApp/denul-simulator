# -*- coding: utf-8 -*-
"""Simulator to simulate the behaviour of users in the system.

The simulator aims to model users joining, leaving and using the system.
"""

import simpy
import random
from progressbar import ProgressBar, Percentage, Bar, ETA
from multiprocessing import Pool, cpu_count
from collections import Counter
import os

SIMULATION_ROUNDS = 201
SIMULATION_ITERATIONS = 4
ITERATION_OFFSET = 1
INITIAL_USERS = 100000


def prepare_network(env, n, m, seed=None):
    """Generate a random graph with the Barabasi-Albert model.

    A graph of ``n`` nodes is grown by attaching new nodes each with ``m``
    edges that are preferentially attached to existing nodes with high degree.

    Parameters
    ----------
    env : Environment
        SimPy environment to use as a base for the graph
    n : int
        Number of nodes
    m : int
        Number of edges to attach from a new node to existing nodes
    seed : int, optional
        Seed for random number generator (default=None).

    Returns
    -------
    env : Environment with Graph set up

    References
    ----------
    .. [1] A. L. Barabasi and R. Albert "Emergence of scaling in
       random networks", Science 286, pp 509-512, 1999.

    Attribution:
    ------------
    Code adapted from the NetworkX project, licensed under the BSD license.
    https://github.com/networkx/networkx/blob/master/networkx/generators/random_graphs.py#L601
    """
    if m < 1 or m >= n:
        raise AssertionError("Barabási-Albert network must have m >= 1"
                             " and m < n, m = %d, n = %d" % (m, n))
    if seed is not None:
        random.seed(seed)

    # Add initial nodes
    env.active_users = [User(env) for i in range(m)]
    # Target nodes for new edges
    targets = env.active_users
    # List of existing nodes, with nodes repeated once for each adjacent edge
    env.repeated_nodes = []
    # Start adding the other n-m nodes. The first node is m.
    source = m
    while source < n:
        # Add edges to m nodes from the source.
        newuser = User(env)
        env.active_users.append(newuser)
        newuser.friends += targets
        for user in targets:
            user.friends += [newuser]
        # Add one node to the list for each new edge just created.
        env.repeated_nodes.extend(targets)
        # And the new node "source" has m edges to add to the list.
        env.repeated_nodes.extend([newuser] * m)
        # Now choose m unique nodes from the existing nodes
        # Pick uniformly from repeated_nodes (preferential attachement)
        targets = _random_subset(env.repeated_nodes, m)
        source += 1
    return env


def _random_subset(seq, m):
    """Return m unique elements from seq.

    This differs from random.sample which can return repeated
    elements if seq holds repeated elements.

    Attribution:
    Code adapted from the NetworkX project, licensed under the BSD license.
    https://github.com/networkx/networkx/blob/master/networkx/generators/random_graphs.py#L589
    """
    targets = set()
    while len(targets) < m:
        x = random.choice(seq)
        if x.active:
            targets.add(x)
    return targets


class User(object):
    """User class - simulates behaviour of a single user."""

    def __init__(self, env):
        """Initialization function."""
        # Environment
        self.env = env
        # The process that performs the simulation work
        self.action = env.process(self.run())
        # Friends
        self.friends = []
        # Number of pieces of data shared
        self.shares = 0
        # Number of share operations performed
        self.share_ops = 0
        # Last share happened at timestep
        self.last_share = 0
        # Status of the user - False means user has stopped using the system
        self.active = True
        # Simulation step in which the user has joined the system
        self.joined = env.now
        # Simulation step in which the user has left the system
        self.left = -1
        # Received, dowloaded shares
        self.shares_downloaded = 0
        # Received, but not yet downloaded shares
        self.shares_received = 0

    def friend_threshold(self):
        """Determine probability of making new friends."""
        return 0.3

    def retrieve_threshold(self):
        """Determine probability of retrieving data from server."""
        return 0.5

    def share_threshold(self):
        """Determine probability of sharing data."""
        return 0.1 + (self.env.now - self.last_share) * 0.1

    def quit_threshold(self):
        """Determine probability of stopping to use the system."""
        # return pow(0.1, len(self.friends))
        return 0.01

    def run(self):
        """Main simulation loop."""
        while self.active:
            self.retrieve_data()
            self.share_data()
            self.quit_application()
            yield self.env.timeout(1)

    def retrieve_data(self):
        """Retrieve incoming shares, with a certain probability."""
        if random.random() < self.retrieve_threshold():
            self.shares_downloaded += self.shares_received
            self.shares_received = 0

    def share_data(self):
        """Share data with all friends, with a certain probability."""
        if random.random() < self.share_threshold():
            # If data is shared, received shares are also retrieved
            self.shares_downloaded += self.shares_received
            self.shares_received = 0
            # Incr. the number of sent shares to 1 plus the number of friends,
            # as we are uploading one data block and n key blocks
            self.shares += 1 + len(self.friends)
            self.share_ops += 1
            # Set the timestamp of the last sent share to now
            self.last_share = self.env.now
            # For each friend, increment the number of received shares
            for friend in self.friends:
                friend.shares_received += 1

    def quit_application(self):
        """Quit using the application, with a certain probability."""
        if random.random() < self.quit_threshold():
            self.active = False
            self.left = self.env.now
            self.env.inactive_users.append(self)
            self.env.active_users.remove(self)
            # self.env.repeated_nodes[:] = [x for x in self.env.repeated_nodes if x != self]


def print_dist(env):
    """Print the current node degree distribution."""
    os.system('clear')
    c = Counter([len(x.friends) for x in env.active_users] + [len(x.friends) for x in env.inactive_users])
    k = 0
    for i in c.keys():
        k = max(k, c[i])
    for i in sorted(c.keys()):
        if (i > 40):
            break
        print i, c[i], "\t", "=" * int((c[i] / float(k)) * 70)


def add_users(env):
    """Add new users to the system."""
    # Add new users to the system
    # env.active_users += [User(env) for i in range(random.randrange(0, 5, 1))]
    # print "step", env.now - 1, millis_poss - millis_pres, (millis_poss - float(millis_pres)) / len(env.active_users), "per user,", len(env. active_users), "users"
    for i in range(random.randrange(int(INITIAL_USERS * 0.01), int(INITIAL_USERS * 0.05), 1)):
        newuser = User(env)
        role_model = _random_subset(env.active_users, 1).pop()
        # print len(role_model.friends), len(env.repeated_nodes), len(env.active_users)
        newfriends = _random_subset(env.repeated_nodes, len(role_model.friends))
        newuser.friends += newfriends
        for friend in newfriends:
            friend.friends.append(newuser)
        env.repeated_nodes.extend([newuser] * len(role_model.friends))
        env.repeated_nodes.extend(newfriends)
        env.active_users.append(newuser)


def save_stats(env):
    """Determine stats and save them to a dictionary."""
    active = len(env.active_users)
    inactive = len(env.inactive_users)
    shares = 0
    friends = 0
    nodownload = 0
    inac_friends = 0
    share_ops = 0
    neverdownload = 0
    # Iterate over all users, active and inactive
    for user in env.active_users:
        shares += user.shares
        share_ops += user.share_ops
        neverdownload += user.share_ops
        friends += len(user.friends)
        nodownload = nodownload + user.shares - user.shares_downloaded
        for uf in user.friends:
            if not uf.active:
                inac_friends += 1
    for user in env.inactive_users:
        shares += user.shares
        share_ops += user.share_ops
        friends += len(user.friends)
        nodownload = nodownload + user.shares - user.shares_downloaded
        neverdownload += user.shares_received
        for uf in user.friends:
            if not uf.active:
                inac_friends += 1
    # Length distribution
    ctr = Counter([len(x.friends) for x in env.active_users])
    # Add result to return value
    return {
        "users": active + inactive,
        "users_active": active,
        "users_inactive": inactive,
        "shares": shares,
        "share_ops": share_ops,
        "share_noretr": nodownload,
        "share_neverretr": neverdownload,
        "friends": friends,
        "friends_inactive": inac_friends,
        "friend_distribution": ctr
    }


def run(iteration):
    """Main simulation control loop."""
    env = simpy.Environment()
    env = prepare_network(env, INITIAL_USERS, 1)
    env.inactive_users = []

    results = {}

    # time_pre = int(round(time.time() * 1000))
    results[0] = save_stats(env)

    while env.peek() < SIMULATION_ROUNDS:
        last = env.now != env.peek()
        if last:
            # The next step will be the first in the next simulation timestep
            # print_dist(env)
            if env.peek() % 10 == 0:
                # Ten steps have passed, gather statistics
                results[env.now + 1] = save_stats(env)
                # Clean up the list of repeated nodes
                env.repeated_nodes[:] = [x for x in env.repeated_nodes if x.active]
        env.step()
        if last:
            add_users(env)
            # print env.now, int(round(time.time() * 1000)) - time_pre, len(env.active_users)
            # time_pre = int(round(time.time() * 1000))
    return results

# Prepare ProgressBar
widgets = [Percentage(), Bar(marker='=', left='[', right=']'),
           ' ', ETA()]
pbar = ProgressBar(widgets=widgets)

# Prepare multiprocessing Pool
try:
    pool = Pool(processes=min(cpu_count(), SIMULATION_ITERATIONS))
except NotImplementedError:
    print "Could not determine CPU count, using 4"
    pool = Pool(processes=4)

# Multiprocess simulation
resiter = pool.imap(run, range(SIMULATION_ITERATIONS))
# Retrieve and save results
with open('rounds.csv', 'w') as rounds, open('dist.csv', 'w') as dist:
    rounds.write("iteration round users active inactive shares shareops nodownload neverdownload friends inacfriends\n")
    dist.write("iteration round degree count\n")
    for i in pbar(range(SIMULATION_ITERATIONS)):
        res = resiter.next()
        # res = run(i)
        for k in sorted(res.keys()):
            rounds.write(str(i + ITERATION_OFFSET) + " " + str(k) + " " +
                         str(res[k]["users"]) + " " +
                         str(res[k]["users_active"]) + " " +
                         str(res[k]["users_inactive"]) + " " +
                         str(res[k]["shares"]) + " " +
                         str(res[k]["share_ops"]) + " " +
                         str(res[k]["share_noretr"]) + " " +
                         str(res[k]["share_neverretr"]) + " " +
                         str(res[k]["friends"]) + " " +
                         str(res[k]["friends_inactive"]) + "\n")
            for degree in sorted(res[k]["friend_distribution"].keys()):
                dist.write(str(i + ITERATION_OFFSET) + " " + str(k) + " " +
                           str(degree) + " " +
                           str(res[k]["friend_distribution"][degree]) + "\n")
        rounds.flush()
        dist.flush()


# Print aggregated statistics
# TODO Commented out due to pypy / numpy incompatibilities
# with open('results.csv', 'w') as fo:
#     fo.write("round user_median user_1q user_3q user_min user_max " +
#              "active_user_median active_user_1q active_user_3q active_user_min active_user_max " +
#              "inactive_user_median inactive_user_1q inactive_user_3q inactive_user_min inactive_user_max " +
#              "share_median shares_1q shares_3q shares_min shares_max " +
#              "shareops_median shareops_1q shareops_3q shareops_min shareops_max " +
#              "sharenoretr_median sharenoretr_1q sharenoretr_3q sharenoretr_min sharenoretr_max " +
#              "friends_median friends_1q friends_3q friends_min friends_max " +
#              "finactive_median finactive_1q finactive_3q finactive_min finactive_max\n")
#
#     for k in sorted(res[0].keys()):
#         users = [res[i][k]["users"] for i in range(SIMULATION_ITERATIONS)]
#         uactive = [res[i][k]["users_active"] for i in range(SIMULATION_ITERATIONS)]
#         uinactive = [res[i][k]["users_inactive"] for i in range(SIMULATION_ITERATIONS)]
#         shares = [res[i][k]["shares"] for i in range(SIMULATION_ITERATIONS)]
#         shareops = [res[i][k]["share_ops"] for i in range(SIMULATION_ITERATIONS)]
#         share_noretr = [res[i][k]["share_noretr"] for i in range(SIMULATION_ITERATIONS)]
#         friends = [res[i][k]["friends"] for i in range(SIMULATION_ITERATIONS)]
#         finactive = [res[i][k]["friends_inactive"] for i in range(SIMULATION_ITERATIONS)]
#         fo.write(str(k) + " " +
#                  str(numpy.percentile(users, 50)) + " " +
#                  str(numpy.percentile(users, 25)) + " " +
#                  str(numpy.percentile(users, 75)) + " " +
#                  str(numpy.min(users)) + " " +
#                  str(numpy.max(users)) + " " +
#                  str(numpy.percentile(uactive, 50)) + " " +
#                  str(numpy.percentile(uactive, 25)) + " " +
#                  str(numpy.percentile(uactive, 75)) + " " +
#                  str(numpy.min(uactive)) + " " +
#                  str(numpy.max(uactive)) + " " +
#                  str(numpy.percentile(uinactive, 50)) + " " +
#                  str(numpy.percentile(uinactive, 25)) + " " +
#                  str(numpy.percentile(uinactive, 75)) + " " +
#                  str(numpy.min(uinactive)) + " " +
#                  str(numpy.max(uinactive)) + " " +
#                  str(numpy.percentile(shares, 50)) + " " +
#                  str(numpy.percentile(shares, 25)) + " " +
#                  str(numpy.percentile(shares, 75)) + " " +
#                  str(numpy.min(shares)) + " " +
#                  str(numpy.max(shares)) + " " +
#                  str(numpy.percentile(shareops, 50)) + " " +
#                  str(numpy.percentile(shareops, 25)) + " " +
#                  str(numpy.percentile(shareops, 75)) + " " +
#                  str(numpy.min(shareops)) + " " +
#                  str(numpy.max(shareops)) + " " +
#                  str(numpy.percentile(share_noretr, 50)) + " " +
#                  str(numpy.percentile(share_noretr, 25)) + " " +
#                  str(numpy.percentile(share_noretr, 75)) + " " +
#                  str(numpy.min(share_noretr)) + " " +
#                  str(numpy.max(share_noretr)) + " " +
#                  str(numpy.percentile(friends, 50)) + " " +
#                  str(numpy.percentile(friends, 25)) + " " +
#                  str(numpy.percentile(friends, 75)) + " " +
#                  str(numpy.min(friends)) + " " +
#                  str(numpy.max(friends)) + " " +
#                  str(numpy.percentile(finactive, 50)) + " " +
#                  str(numpy.percentile(finactive, 25)) + " " +
#                  str(numpy.percentile(finactive, 75)) + " " +
#                  str(numpy.min(finactive)) + " " +
#                  str(numpy.max(finactive)) + "\n")
