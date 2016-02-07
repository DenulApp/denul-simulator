"""Simulator to simulate the behaviour of users in the system.

The simulator aims to model users joining, leaving and using the system.
"""

import simpy
import random

SIMULATION_ROUNDS = 361
INITIAL_USERS = 100


class User(object):
    """User class - simulates behaviour of a single user."""

    def __init__(self, env):
        """Initialization function."""
        # Environment
        self.env = env
        # The process that performs the simulation work
        self.action = env.process(self.run())
        # Number of friends
        self.friends = 0
        # Number of pieces of data shared
        self.shares = 0
        # Last share happened at timestep
        self.last_share = 0
        # Status of the user - False means user has stopped using the system
        self.active = True
        # Simulation step in which the user has joined the system
        self.joined = env.now
        # Simulation step in which the user has left the system
        self.left = -1

    def run(self):
        """Main simulation loop."""
        while self.active:
            self.make_friends()
            self.share_data()
            self.quit_application()
            yield self.env.timeout(1)

    def make_friends(self):
        """Make new friends, with a certain probability."""
        if random.random() < 0.3:
            self.friends += 1

    def share_data(self):
        """Share data with all friends, with a certain probability."""
        if random.random() < 0.1 + (self.env.now - self.last_share) * 0.1:
            self.shares += 1 + self.friends
            self.last_share = self.env.now

    def quit_application(self):
        """Quit using the application, with a certain probability."""
        if random.random() < 0.01:
            self.active = False
            self.left = self.env.now
            self.env.inactive_users.append(self)
            self.env.active_users.remove(self)


env = simpy.Environment()
env.active_users = [User(env) for i in range(INITIAL_USERS)]
env.inactive_users = []


while env.peek() < SIMULATION_ROUNDS:
    last = env.now != env.peek()
    if last:
        # The next step will be the first in the next simulation timestep
        if env.peek() % 10 == 0:
            # Ten steps have passed, gather data
            print "Step", env.now + 1
            active = len(env.active_users)
            inactive = len(env.inactive_users)
            shares = 0
            friends = 0
            for user in env.active_users:
                shares += user.shares
                friends += user.friends
            print "  Active:  ", active
            print "  Inactive:", inactive
            print "  Shares:  ", shares
            print "  Friends: ", friends
    env.step()
    if last:
        env.active_users += [User(env) for i in range(random.randrange(0, 5, 1))]


# Complex model: More realistic, but a lot more work
# - Users joining
#   With which distribution?
# - Users leaving
#   With which distribution?
# - Users becoming friends
#   Achieve power-law distribution in friend count
# - Users sharing data
#   Between once per Month and once per day, peaking at three times a week
# - Users retrieving data
#   When?
