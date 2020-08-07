""" The graphical rendering part of the project
    Uses the values from the engine to describe the world.
    Still need to decide on the modules to be used.
"""
import time
import math
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib.widgets import Slider, CheckButtons
import numpy as np

import world

def render_community(steps, env,
                     community: world.Community,
                     before_callback=None, before_args=None, before_kwargs=None,
                     after_callback=None, after_args=None, after_kwargs=None,
                     interval=100):
    """Renders a single community

        Parameters:
            - steps: Number of steps to run for. Use 0 or negative to simulate indefinitely
            - env: SimPy Environment (TODO: might not be required)
            - community: the community object to simulate
            - before_callback: a function to call before rendering each frame. Arguments to this
                function can be given using before_args and before_kwargs
            - after_callback: a function to call after rendering each frame. Arguments to this
                function can be given using after_args and after_kwargs
            - interval: time between each frame in ms
    """
    # initialize optional args here to avoid python quirks
    if not before_args:
        before_args = []
    if not after_args:
        after_args = []
    if not before_kwargs:
        before_kwargs = dict()
    if not after_kwargs:
        after_kwargs = dict()

    # if number of steps is negative or zero, run forever
    infinite = False
    if steps <= 0:
        infinite = True
        steps = None

    # make subplots, only 1 subplot (with graph) since this function only simulates one community
    fig, ax = plt.subplots(1, 2, figsize=(16, 9))

    # set limits and aspect ratio for community plot
    plt.subplots_adjust(left=0.25, bottom=0.25)
    ax[0].set_aspect('equal')
    ax[0].set_xlim(community.position[0][0]-2, community.position[0][1]+2)
    ax[0].set_ylim(community.position[1][0]-2, community.position[1][1]+2)

    # set limits, labels and aspect ratio for infected percent plot
    ax[1].set_aspect(10)
    ax[1].set_ylim(0, 101)
    ax[1].set_xlim(0, 1000)
    ax[1].set_xlabel("Time")
    ax[1].set_ylabel("Percent of infected")
    timesteps = [] # to store x values of infected percent plot
    infected_percentages = [] # y values
    infected_percent_plot, = ax[1].plot([], []) # initial plot

    # make axes for sliders and buttons
    axcolor = 'lightgoldenrodyellow'
    ax_slider_1 = plt.axes([0.25, 0.1, 0.65, 0.03], facecolor=axcolor)
    ax_slider_2 = plt.axes([0.25, 0.15, 0.65, 0.03], facecolor=axcolor)
    ax_slider_3 = plt.axes([0.25, 0.2, 0.65, 0.03], facecolor=axcolor)
    ax_slider_4 = plt.axes([0.25, 0.01, 0.65, 0.03], facecolor=axcolor)
    ax_slider_5 = plt.axes([0.25, 0.05, 0.65, 0.03], facecolor=axcolor)
    ax_left_1 = plt.axes([0.025, 0.5, 0.15, 0.10], facecolor=axcolor)


    # For displaying R value
    ax_left_2 = plt.axes([0.01, 0.8, 0.2, 0.05])
    ax_left_2.get_xaxis().set_visible(False)
    ax_left_2.get_yaxis().set_visible(False)
    ax_left_2_bbox = ax_left_2.get_position(original=False).get_points()
    r_value_x = (ax_left_2_bbox[0][0] + ax_left_2_bbox[0][1]) / 2.0
    r_value_y = (ax_left_2_bbox[1][0] + ax_left_2_bbox[1][1]) / 2.0
    r_text = ax_left_2.text(r_value_x, r_value_y,
                            "R value:",
                            horizontalalignment='center',
                            verticalalignment='center')

    # For displaying infected percentage
    ax_left_3 = plt.axes([0.01, 0.9, 0.2, 0.05])
    ax_left_3.get_xaxis().set_visible(False)
    ax_left_3.get_yaxis().set_visible(False)
    ax_left_3_bbox = ax_left_3.get_position(original=False).get_points()
    infected_percent_x = (ax_left_3_bbox[0][0] + ax_left_3_bbox[0][1]) / 2.0
    infected_percent_y = (ax_left_3_bbox[1][0] + ax_left_3_bbox[1][1]) / 2.0
    infected_percent_text = ax_left_3.text(infected_percent_x, infected_percent_y,
                                           "Percent infected:",
                                           horizontalalignment='center',
                                           verticalalignment='center')

    max_walk_range = round(math.sqrt((community.position[0][1]-community.position[0][0])**2
                                     + (community.position[1][1]-community.position[1][0])**2))
    initial_walk_range = max_walk_range / 2
    community.set_people_attribute("walk_range", initial_walk_range)
    # slider to control walk_range
    walk_range_slider = Slider(ax_slider_1, "Walk Range", 1, max_walk_range,
                               valinit=initial_walk_range,
                               valstep=1)
    # slider to control stop_duration
    stop_duration_slider = Slider(ax_slider_2, "Stop Duration", 1, 1000, valinit=25, valstep=1)
    # slider to control probability of going to a popular place
    pop_place_slider = Slider(ax_slider_3, "Prob of going to popular place", 0, 1, valinit=0.3)
    # slider to control infect range
    infect_range_slider = Slider(ax_slider_4, "Infect range", 0, max_walk_range/2, valinit=2, valstep=0.5)
    # slider to control infect probability
    infect_prob_slider = Slider(ax_slider_5, "Infect prob", 0, 0.5, valinit=0.01, valstep=0.001)

    # common function to upload all sliders
    def update_sliders(_):
        community.set_people_attribute("walk_range", walk_range_slider.val)
        community.set_people_attribute("stop_duration", stop_duration_slider.val)
        community.set_people_attribute("popular_place_probability", pop_place_slider.val)
    def update_infect_sliders(_):
        community.set_people_attribute("infect_range", infect_range_slider.val)
        community.set_people_attribute("infect_probability", infect_prob_slider.val)
    # attach sliders to update function
    walk_range_slider.on_changed(update_sliders)
    stop_duration_slider.on_changed(update_sliders)
    pop_place_slider.on_changed(update_sliders)
    infect_range_slider.on_changed(update_infect_sliders)
    infect_prob_slider.on_changed(update_infect_sliders)

    num_people = len(community.population)

    # initialize the scatter plot
    normal_color = 0.5 # color of non-infected people (green)
    infected_color = 0.9 # color of infected people (red)
    data, _, _ = community.get_all_positions_colors(normal_color, infected_color)
    x = data[:, 0]
    y = data[:, 1]
    c = data[:, 2] # intialize color
    scat = ax[0].scatter(x, y, c=c, vmin=0, vmax=1,
                         cmap="jet", edgecolor="k")
    # plot popular places
    pop_places_x = [pos[0] for pos in community.popular_places]
    pop_places_y = [pos[1] for pos in community.popular_places]
    pop_scat = ax[0].scatter(pop_places_x,
                             pop_places_y,
                             marker="s",
                             alpha=0.5)

    # utility function to update key-value args with local variables
    def change_kwargs(orig_kwargs, **kwargs):
        orig_kwargs.update(kwargs)

    frame_count = 0
    total_frametime = 0
    def update(frame):
        """Update the scatter plot."""
        nonlocal total_frametime, frame_count, data

        # store time at beginning of frame calc
        begin_time = time.perf_counter()

        # call the "before" function
        if before_callback:
            before_callback(*before_args, **before_kwargs)

        data, r_value, infected_percent = community.get_all_positions_colors(normal_color,
                                                                             infected_color,
                                                                             nparray_to_fill=data)

        # Set x and y data (input in the form of a 2D np array)
        scat.set_offsets(data[:, 0:2])

        # Set sizes of dots (we might not need this)
        # self.scat.set_sizes(300 * abs(data[:, 2])**1.5 + 100)

        # Set colors of dots
        scat.set_array(data[:, 2])

        # update R value text
        r_text.set_text("R Value: {:3.2f}".format(r_value))
        # updated infected percent text
        infected_percent_text.set_text("Percent infected: {:3.2f}%".format(infected_percent))

        # call the "after" function
        if after_callback:
            after_callback(*after_args, **after_args)

        if frame % 10 == 0:
            infected_percentages.append(infected_percent) # updated infected percent list
            timesteps.append(frame) # updated x values for infected percent plot
            # check if frame number exceeds x limit
            xlim_min, xlim_max = ax[1].get_xlim()
            if frame > xlim_max:
                # update x limit if it exceeds
                ax[1].set_xlim(xlim_min, xlim_max + 500)
            # update infected percent plot
            infected_percent_plot.set_data(timesteps, infected_percentages)

        # time after major calcs
        total_time = time.perf_counter() - begin_time
        # convert to microseconds and round off to 2 decimal places
        frametime = round(total_time*1000000, 2)
        # store total frametime (to calculate compute time)
        # not exactly the frame time (most of the time is probably spent in drawing)
        total_frametime += frametime
        frame_count += 1

        if frame_count == 100:
            # log compute time every 100 frames
            print("Average compute time in last {} frames: {:8.2f} microseconds".format(
                frame_count,
                total_frametime/frame_count))
            frame_count = 0
            total_frametime = 0

        # We need to return the updated artist for FuncAnimation to draw..
        # Note that it expects a sequence of artists, thus the trailing comma.
        return (scat, r_text, infected_percent_text, infected_percent_plot)

    anim = animation.FuncAnimation(fig, update, interval=interval,
                                   blit=True,
                                   repeat=infinite,
                                   frames=steps)

    anim_running = True # to keep track of the animation state

    def onClick(_):
        """Toggles between pause and resume of the animation"""
        nonlocal anim_running
        if anim_running:
            anim.event_source.stop()
            anim_running = False
        else:
            anim.event_source.start()
            anim_running = True
        ax[0].draw_artist(scat)
        ax[1].draw_artist(infected_percent_plot)

    # add a button widget to pause
    pause_button = CheckButtons(ax_left_1, ["Pause"])
    pause_button.on_clicked(onClick)
    # fig.canvas.mpl_connect('button_press_event', onClick)

    plt.show()

if __name__ == "__main__":
    pass
