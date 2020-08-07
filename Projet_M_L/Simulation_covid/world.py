import random

import numpy as np
import simpy

from spatialhash import PersonSpatialHash

CLOSE_ENOUGH_THRESHOLD = 0.5
WALK_SPEED = 1.0

def random_tf(probability):
    """Returns True probability% of times (has been tested)
    """
    if random.random() < probability:
        return True
    return False

class Person:
    """ A person in our simulation model, these objects live the box models.
        They need these properties:
        1. Which box they belong to, given at init (Not needed?)
            1.1 Also a unique ID to identify them (probably not needed, but useful for debugging)
        2. Location within the box, also given at init
        3. Infected state, false at init
        4. Time since infection. (Needs to be handled by simpy)
        5. Boundaries of the box they are in (given at init)
        6. List of popular places in the community with the probability of going to such places
    """

    def __init__(self, person_id, start_pos, boundaries, env: simpy.Environment, popular_places):
        self.id_ = person_id
        self.position = start_pos
        self.infected = False
        self.time_infected = -1  # Invalid means not infected
        self.infect_range = 2  # max range in which a person can a infect another
        self.infect_probability = 0.01  # probability of infecting people in range
        self.num_infected = 0  # to keep track of number of people this person infected
        self.walk_range = 5  # max distance a person can go after stopping
        # randomly initialise walking speed of this person
        self.walk_speed = random.random() * WALK_SPEED
        self.walk_duration = 10 # max duration (in terms of simpy env steps) to walk for
        self.stop_duration = 25 # same as above, but for being in one place
        self.env = env # simpy environment
        self.boundaries = boundaries  # (x_min, x_max, y_min, y_max)
        self.popular_places = popular_places  # a list of popular places in the community
        self.popular_place_probability = 0.3  # probability of going to a popular place

    def activate(self, spatialhash):
        """Activates an infinite loop of walking and stopping
        """
        while True:
            yield self.env.process(self.wander(spatialhash))  # wander
            yield self.env.timeout(random.randrange(self.stop_duration))  # stop wandering

    def got_infected(self):
        """Make person infected if not already infected"""
        if self.infected:
            return False
        self.infected = True
        self.time_infected = self.env.now
        return True

    def wander(self, spatialhash):
        """ The random walk the particle will be doing till the end of the simulation.
            This doesn't have to be a class method, but will be convenient.
            The particle will wander in the boundaries.
            Need to define per call shift range. i.e how much movement per step

            Times out for some time before actually updating the position.
            It would be better if it moved one position per time step, instead
            of teleporting to the location.
        """
        (start_x, end_x), (start_y, end_y) = self.boundaries
        cur_x, cur_y = self.position

        if self.popular_places and random_tf(self.popular_place_probability):
            new_x, new_y = random.choice(self.popular_places) # go to one of popular places
        else:
            # go to random location in community
            new_x = random.uniform(0, self.walk_range) + cur_x
            new_y = random.uniform(0, self.walk_range) + cur_y
            # Try to move within the correct boundaries
            while not start_x <= new_x <= end_x or not start_y <= new_y <= end_y:
                new_x = random.uniform(-self.walk_range, self.walk_range+1) + cur_x
                new_y = random.uniform(-self.walk_range, self.walk_range+1) + cur_y

        def get_direction(position, target):
            """Given current value and target value return direction of increase to reach target"""
            if not close_enough(position, target):
                if position < target:
                    return 1
                if position > target:
                    return -1
            return 0

        def close_enough(current_value, target_value):
            """Returns whether current_value is close enough to target value based on threshold"""
            if abs(current_value - target_value) < CLOSE_ENOUGH_THRESHOLD:
                return True
            return False

        # move slowly to target (not just teleport to it)
        while not close_enough(cur_x, new_x) or not close_enough(cur_y, new_y):
            direction = (get_direction(cur_x, new_x), get_direction(cur_y, new_y))
            # increment position
            cur_x += direction[0] * self.walk_speed
            cur_y += direction[1] * self.walk_speed
            if self.infected:
                # if infected do a spatial search
                nearby_people = spatialhash.search_nearby(self, self.infect_range)
                for nearby_person in nearby_people:
                    # infect nearby people
                    if random_tf(self.infect_probability):
                        # infect successful
                        self.num_infected += (nearby_person.got_infected())
            # update position in spatial hash
            spatialhash.updateObject(self, cur_x, cur_y)
            self.position = cur_x, cur_y # update position in object
            yield self.env.timeout(1)

class Community:
    """ A community in our model world, they are represented by boxes.
        There are also isolation communities. They are rendered on the 'Canvas'
        The particles move around within the boundaries of the box. In some rare cases
        they are allowed to travel(and spread the virus, what fun!)
        The properties these objects need to have are:
        1. The people in the communites, can be a list
        2. Position within the canvas
        3. Lockdown?
    """

    def __init__(self, position, env: simpy.Environment, no_of_people=60, popular_places=None):
        self.position = position  # defines boundaries of the community
        self.env = env  # SimPy environment
        self.population = []
        (start_x, end_x), (start_y, end_y) = position

        # this will be a list of popular places in the community which
        # most of the residents will frequently visit
        if not popular_places:
            popular_places = []
        self.popular_places = popular_places

        self.count = no_of_people

        # initialise spatial hash table
        self.spatialhash = PersonSpatialHash(cell_size=3)

        self.initial_infected_percent = 0.05
        for person_id in range(no_of_people):
            # randomly spawn person
            start_pos = (random.uniform(start_x, end_x), random.uniform(start_y, end_y))
            new_person = Person(person_id, start_pos, position, env, popular_places)
            if random_tf(self.initial_infected_percent):
                # randomly infect that person
                new_person.got_infected()
            self.population.append(new_person)
            self.spatialhash.insertObject(new_person) # insert to spatial hash
        self.population_processes = []  # to store the SimPy processes for each person
        # ^ this could be dict

    def get_all_positions_colors(self, normal_color, infected_color, nparray_to_fill=None):
        """Get positions of all people in the form of two separate x and y lists.
        This is a helper function for plotting.
        """
        num_infecteds = []  # to store number of people infected by each person
        total_infected = 0  # to store number of infected people
        if nparray_to_fill is None:
            data = np.empty((self.count, 3))  # initialise data array
        else:
            data = nparray_to_fill  # use data array if given
        for index, person in enumerate(self.population):
            data[index] = (person.position[0],  # x value
                           person.position[1],  # y value
                           infected_color if person.infected else normal_color) # color
            num_infecteds.append(person.num_infected)
            total_infected += int(person.infected)
        # TODO: Probably wrong calculation
        # calculate R value
        r_value = float(sum(num_infecteds))/total_infected
        # calculate percent of infected people
        infected_percent = 100 * float(total_infected)/self.count
        return data, r_value, infected_percent

    def set_people_attribute(self, attr_name, value):
        """Sets an attribute for all people in the population"""
        for person in self.population:
            setattr(person, attr_name, value)

    def activate(self):
        """Activates all the people in this community. This will not lock the thread.
        """
        for person in self.population:
            self.population_processes.append(self.env.process(person.activate(self.spatialhash)))
        return self.population_processes
