#!/usr/bin/env python
import rospy
from std_msgs.msg import Int32
from geometry_msgs.msg import PoseStamped, Pose
from styx_msgs.msg import TrafficLightArray, TrafficLight
from styx_msgs.msg import Lane
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
from light_classification.tl_classifier import TLClassifier
import tf
import cv2
import yaml

import math
import os

STATE_COUNT_THRESHOLD = 3

class TLDetector(object):
    def __init__(self):
        rospy.init_node('tl_detector')

        self.pose = None
        self.waypoints = None
        self.camera_image = None
	self.image_n=0
	self.img_sv = False # TRUE to save images at /home/student/CarND-Capstone/ros/
        self.lights = []

        sub1 = rospy.Subscriber('/current_pose', PoseStamped, self.pose_cb)
        sub2 = rospy.Subscriber('/base_waypoints', Lane, self.waypoints_cb)

        '''
        /vehicle/traffic_lights provides you with the location of the traffic light in 3D map space and
        helps you acquire an accurate ground truth data source for the traffic light
        classifier by sending the current color state of all traffic lights in the
        simulator. When testing on the vehicle, the color state will not be available. You'll need to
        rely on the position of the light and the camera image to predict it.
        '''
        sub3 = rospy.Subscriber('/vehicle/traffic_lights', TrafficLightArray, self.traffic_cb)
        sub6 = rospy.Subscriber('/image_color', Image, self.image_cb)

        config_string = rospy.get_param("/traffic_light_config")
        self.config = yaml.load(config_string)

        self.upcoming_red_light_pub = rospy.Publisher('/traffic_waypoint', Int32, queue_size=1)

        self.bridge = CvBridge()
        self.light_classifier = TLClassifier()
        self.listener = tf.TransformListener()

        self.state = TrafficLight.UNKNOWN
        self.last_state = TrafficLight.UNKNOWN
        self.last_wp = -1
        self.state_count = 0
	
	
        if self.img_sv:
            if not (os.path.exists("./tl_detector_images")):
                os.mkdir("./tl_detector_images")
            self.image_n = 0
	
	#img_init = self.light_classifier.load_image_into_numpy_array(np.zeros((800,600,3)))
        #self.light_classifier.get_localization(img_init)

        rospy.spin()

    def pose_cb(self, msg):
        self.pose = msg
	#self.position = msg.pose.position
        #self.orientation = msg.pose.orientation

    def waypoints_cb(self, waypoints):
        self.waypoints = waypoints.waypoints

    def traffic_cb(self, msg):
        self.lights = msg.lights

    def image_cb(self, msg):
        """Identifies red lights in the incoming camera image and publishes the index
            of the waypoint closest to the red light's stop line to /traffic_waypoint
        Args:
            msg (Image): image from car-mounted camera
        """
        self.has_image = True
        self.camera_image = msg
        light_wp, state = self.process_traffic_lights()

        '''
        Publish upcoming red lights at camera frequency.
        Each predicted state has to occur `STATE_COUNT_THRESHOLD` number
        of times till we start using it. Otherwise the previous stable state is
        used.
        '''
        if self.state != state:
            self.state_count = 0
            self.state = state
        elif self.state_count >= STATE_COUNT_THRESHOLD:
            self.last_state = self.state
            light_wp = light_wp if state == TrafficLight.RED else -1
            self.last_wp = light_wp
            self.upcoming_red_light_pub.publish(Int32(light_wp))
        else:
            self.upcoming_red_light_pub.publish(Int32(self.last_wp))
        self.state_count += 1

	if self.img_sv:
            self.image_save(self.camera_image)

    def image_save(self, image):#saving images
        cv_image = self.bridge.imgmsg_to_cv2(image, "bgr8")
        cv2.imwrite("./tl_detector_images/image{}.jpg".format(self.image_n), cv_image)
        self.image_n += 1	

    def get_closest_waypoint(self, pose):
        """Identifies the closest path waypoint to the given position
            https://en.wikipedia.org/wiki/Closest_pair_of_points_problem
        Args:
            pose (Pose): position to match a waypoint to
        Returns:
            int: index of the closest waypoint in self.waypoints
        """
        #TODO implement
	index = -1        
	if self.waypoints is None:
            return index
        min_dist = 10000
        min_loc = None

        # check all the waypoints to see which one is the closest to our current position
        for i, waypoint in enumerate(self.waypoints):
            wp_x = waypoint.pose.pose.position.x
            wp_y = waypoint.pose.pose.position.y
            dist = math.sqrt((pose.position.x - wp_x)**2 + (pose.position.y - wp_y)**2)
            if (dist < min_dist): #we found a closer wp
                min_loc = i     # we store the index of the closest waypoint
                min_dist = dist     # we save the distance of the closest waypoint

        # returns the index of the closest waypoint
        return min_loc

    def get_light_state(self, light):
        """Determines the current color of the traffic light
        Args:
            light (TrafficLight): light to classify
        Returns:
            int: ID of traffic light color (specified in styx_msgs/TrafficLight)
        """
        if(not self.has_image):
            self.prev_light_loc = None
            return False

        cv_image = self.bridge.imgmsg_to_cv2(self.camera_image, "bgr8")

        #Get classification
        return self.light_classifier.get_classification(cv_image)

    def process_traffic_lights(self):
        """Finds closest visible traffic light, if one exists, and determines its
            location and color
        Returns:
            int: index of waypoint closes to the upcoming stop line for a traffic light (-1 if none exists)
            int: ID of traffic light color (specified in styx_msgs/TrafficLight)
        """
        light = None
 	closest_wp = None
	closest_stop_wp = None

        # List of positions that correspond to the line to stop in front of for a given intersection
        stop_line_positions = self.config['stop_line_positions']

        if(self.pose):
            car_position = self.get_closest_waypoint(self.pose.pose)
	
        #TODO find the closest visible traffic light (if one exists)
	

        if light:
            state = self.get_light_state(light)
            return light_wp, state

	for light_slp in stop_line_positions:
            light_slp_pose = Pose()
            light_slp_pose.position.x = light_slp[0]
            light_slp_pose.position.y = light_slp[1]
            light_slp_wp = self.get_closest_waypoint(light_slp_pose) #found wp closest to each light

            if light_slp_wp >= car_position and (closest_stop_wp is None or light_slp_wp < closest_stop_wp):    # if ahead of the car
                    closest_stop_wp = light_slp_wp
                    light = light_slp_pose


        if ((car_position is not None) and (closest_stop_wp is not None)):
            light_distance = abs(car_position - closest_stop_wp)
	    #rospy.loginfo("Car position:" + str(car_position))
	    rospy.loginfo("Car position:" + str(car_position)+"||"+"Closest light position:"+ str(closest_stop_wp))# Wp index
        rospy.loginfo("light_distance:" + str(light_distance))
        if light and light_distance < 100:       #within 100 waypoints distance
            state = self.get_light_state(light)
            return closest_stop_wp, state

	

        return -1, TrafficLight.UNKNOWN

if __name__ == '__main__':
    try:
        TLDetector()
    except rospy.ROSInterruptException:
        rospy.logerr('Could not start traffic node.')
