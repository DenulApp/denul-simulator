"""Simulator to simulate the behaviour of users in the system.

The simulator aims to model users joining, leaving and using the system.
"""

import simpy
import random

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
        if random.random() < 0.3:
            newfriend = random.sample(self.env.active_users - self.friends, 1)[0]
            self.friends.add(newfriend)
            newfriend.friends.add(self)

    def retrieve_data(self):
        """Retrieve incoming shares, with a certain probability."""
        if random.random() < 0.5:
            self.shares_downloaded += self.shares_received
            self.shares_received = 0

    def share_data(self):
        """Share data with all friends, with a certain probability."""
        if random.random() < 0.1 + (self.env.now - self.last_share) * 0.1:
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
        if random.random() < 0.01:
            self.active = False
            self.left = self.env.now
            self.env.inactive_users.add(self)
            self.env.active_users.remove(self)


def run(stdout=False):
    """Main simulation loop."""
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
                # Print stats
                if stdout:
                    print "Step", env.now + 1
                    print "  Users:      ", active + inactive
                    print "    Active:   ", active
                    print "    Inactive: ", inactive
                    print "  Shares:     ", shares
                    print "    Share ops:", share_ops
                    print "    Not retr: ", nodownload
                    print "  Friends:    ", friends
                    print "    Inactive: ", inac_friends
                else:
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

res = {}
avg = {}
for i in range(SIMULATION_ITERATIONS):
    res[i] = run()

print "iteration round users active inactive shares shareops nodownload friends inacfriends"
for i in range(SIMULATION_ITERATIONS):
    for k in sorted(res[i].keys()):
        print i, k, res[i][k]["users"], res[i][k]["users_active"], \
            res[i][k]["users_inactive"], res[i][k]["shares"], \
            res[i][k]["share_ops"], res[i][k]["share_noretr"], \
            res[i][k]["friends"], res[i][k]["friends_inactive"]
