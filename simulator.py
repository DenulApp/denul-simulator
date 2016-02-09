"""Simulator to simulate the behaviour of users in the system.

The simulator aims to model users joining, leaving and using the system.
"""

import simpy
import random
import numpy
from progressbar import ProgressBar, Percentage, Bar, ETA
from multiprocessing import Pool, cpu_count

SIMULATION_ROUNDS = 361
SIMULATION_ITERATIONS = 10
INITIAL_USERS = 100


class User(object):
    """User class - simulates behaviour of a single user."""

    def __init__(self, env):
        """Initialization function."""
        # Environment
        self.env = env
        # The process that performs the simulation work
        self.action = env.process(self.run())
        # Friends
        self.friends = set([])
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
        return 0.01

    def run(self):
        """Main simulation loop."""
        while self.active:
            self.make_friends()
            self.retrieve_data()
            self.share_data()
            self.quit_application()
            yield self.env.timeout(1)

    def make_friends(self):
        """Make new friends, with a certain probability."""
        if random.random() < self.friend_threshold():
            newfriend = random.sample(self.env.active_users - self.friends, 1)[0]
            self.friends.add(newfriend)
            newfriend.friends.add(self)

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
            self.env.inactive_users.add(self)
            self.env.active_users.remove(self)


def run(iteration):
    """Main simulation control loop."""
    env = simpy.Environment()
    env.active_users = set([User(env) for i in range(INITIAL_USERS)])
    env.inactive_users = set([])

    results = {}

    while env.peek() < SIMULATION_ROUNDS:
        last = env.now != env.peek()
        if last:
            # The next step will be the first in the next simulation timestep
            if env.peek() % 10 == 0:
                # Ten steps have passed, gather statistics
                active = len(env.active_users)
                inactive = len(env.inactive_users)
                shares = 0
                friends = 0
                nodownload = 0
                inac_friends = 0
                share_ops = 0
                # Iterate over all users, active and inactive
                for user in env.active_users | env.inactive_users:
                    shares += user.shares
                    share_ops += user.share_ops
                    friends += len(user.friends)
                    nodownload = nodownload + user.shares - user.shares_downloaded
                    inac_friends += len(user.friends & env.inactive_users)
                # Add result to return value
                results[env.now + 1] = {
                    "users": active + inactive,
                    "users_active": active,
                    "users_inactive": inactive,
                    "shares": shares,
                    "share_ops": share_ops,
                    "share_noretr": nodownload,
                    "friends": friends,
                    "friends_inactive": inac_friends
                }
        env.step()
        if last:
            # Add new users to the system
            env.active_users.update([User(env) for i in range(random.randrange(0, 5, 1))])
    return results

# Result dictionary
res = {}

# Prepare ProgressBar
widgets = [Percentage(), Bar(marker='=', left='[', right=']'),
           ' ', ETA()]
pbar = ProgressBar(widgets=widgets)

# Prepare multiprocessing Pool
try:
    pool = Pool(processes=cpu_count())
except NotImplementedError:
    print "Could not determine CPU count, using 4"
    pool = Pool(processes=4)

# Multiprocess simulation
resiter = pool.imap(run, range(SIMULATION_ITERATIONS))
# Retrieve and save results
for i in pbar(range(SIMULATION_ITERATIONS)):
    res[i] = resiter.next(timeout=60)

# Print raw output data, as space-separated values
with open('rounds.csv', 'w') as fo:
    fo.write("iteration,round,users,active,inactive,shares,shareops,nodownload,friends,inacfriends\n")
    for i in range(SIMULATION_ITERATIONS):
        for k in sorted(res[i].keys()):
            fo.write(str(i) + "," + str(k) + "," +
                     str(res[i][k]["users"]) + "," +
                     str(res[i][k]["users_active"]) + "," +
                     str(res[i][k]["users_inactive"]) + "," +
                     str(res[i][k]["shares"]) + "," +
                     str(res[i][k]["share_ops"]) + "," +
                     str(res[i][k]["share_noretr"]) + "," +
                     str(res[i][k]["friends"]) + "," +
                     str(res[i][k]["friends_inactive"]) + "\n")

# Print aggregated statistics
with open('results.csv', 'w') as fo:
    fo.write("round,user_avg,user_stddev,user_min,user_max," +
             "active_user_avg,active_user_stddev,active_user_min,active_user_max," +
             "inactive_user_avg,inactive_user_stddev,inactive_user_min,inactive_user_max," +
             "share_avg,shares_stddev,shares_min,shares_max," +
             "shareops_avg,shareops_stddev,shareops_min,shareops_max," +
             "sharenoretr_avg,sharenoretr_stddev,sharenoretr_min,sharenoretr_max," +
             "friends_avg,friends_stddev,friends_min,friends_max," +
             "finactive_avg,finactive_stddev,finactive_min,finactive_max\n")

    for k in sorted(res[0].keys()):
        users = [res[i][k]["users"] for i in range(SIMULATION_ITERATIONS)]
        uactive = [res[i][k]["users_active"] for i in range(SIMULATION_ITERATIONS)]
        uinactive = [res[i][k]["users_inactive"] for i in range(SIMULATION_ITERATIONS)]
        shares = [res[i][k]["shares"] for i in range(SIMULATION_ITERATIONS)]
        shareops = [res[i][k]["share_ops"] for i in range(SIMULATION_ITERATIONS)]
        share_noretr = [res[i][k]["share_noretr"] for i in range(SIMULATION_ITERATIONS)]
        friends = [res[i][k]["friends"] for i in range(SIMULATION_ITERATIONS)]
        finactive = [res[i][k]["friends_inactive"] for i in range(SIMULATION_ITERATIONS)]
        fo.write(str(k) + "," +
                 str(numpy.average(users)) + "," +
                 str(numpy.std(users)) + "," +
                 str(numpy.min(users)) + "," +
                 str(numpy.max(users)) + "," +
                 str(numpy.average(uactive)) + "," +
                 str(numpy.std(uactive)) + "," +
                 str(numpy.min(uactive)) + "," +
                 str(numpy.max(uactive)) + "," +
                 str(numpy.average(uinactive)) + "," +
                 str(numpy.std(uinactive)) + "," +
                 str(numpy.min(uinactive)) + "," +
                 str(numpy.max(uinactive)) + "," +
                 str(numpy.average(shares)) + "," +
                 str(numpy.std(shares)) + "," +
                 str(numpy.min(shares)) + "," +
                 str(numpy.max(shares)) + "," +
                 str(numpy.average(shareops)) + "," +
                 str(numpy.std(shareops)) + "," +
                 str(numpy.min(shareops)) + "," +
                 str(numpy.max(shareops)) + "," +
                 str(numpy.average(share_noretr)) + "," +
                 str(numpy.std(share_noretr)) + "," +
                 str(numpy.min(share_noretr)) + "," +
                 str(numpy.max(share_noretr)) + "," +
                 str(numpy.average(friends)) + "," +
                 str(numpy.std(friends)) + "," +
                 str(numpy.min(friends)) + "," +
                 str(numpy.max(friends)) + "," +
                 str(numpy.average(finactive)) + "," +
                 str(numpy.std(finactive)) + "," +
                 str(numpy.min(finactive)) + "," +
                 str(numpy.max(finactive)) + "\n")
