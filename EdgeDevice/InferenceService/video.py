import numpy as np
import tensorflow as tf
import cv2
import os

CWD_PATH = os.getcwd()

# Path to frozen detection graph. This is the actual model that is used for the classification.
PATH_TO_CKPT = os.path.join(CWD_PATH, '../models/charades/frozen_model.pb')
PREDICTION_DECAY = 0.6  # [0,1) How slowly to update the predictions (0.99 is slowest, 0 is instant)


class VideoInference:

    def __init__(self):
        self.accumulator = np.zeros(157, )

        # Load a (frozen) Tensorflow model into memory.
        self.detection_graph = tf.Graph()
        with self.detection_graph.as_default():
            od_graph_def = tf.compat.v1.GraphDef()
            with tf.compat.v1.gfile.GFile(PATH_TO_CKPT, 'rb') as fid:
                serialized_graph = fid.read()
                od_graph_def.ParseFromString(serialized_graph)
                tf.import_graph_def(od_graph_def, name='')

            self.sess = tf.compat.v1.Session(graph=self.detection_graph)

        self.category_classes = self.loadlabels('Charades_v1_classes.txt')
        self.category_object = self.loadlabels('Charades_v1_objectclasses.txt')
        self.category_verbclasses = self.loadlabels('Charades_v1_verbclasses.txt')
        self.mapclasses(self.category_classes, self.category_object, self.category_verbclasses)
        # print(self.category_classes)

    def inference(self, frame):
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        prediction = self.recognize_activity(frame_rgb, self.sess, self.detection_graph, self.accumulator)
        return prediction

    def loadlabels(self, file):
        # List of the strings that is used to add correct label for each box.
        labels = {}
        with open('../models/charades/' + file) as f:
            for line in f:
                x = line.split(' ')
                cls, rest = x[0], ' '.join(x[1:]).strip()
                clsint = int(cls[1:])
                labels[clsint] = {'id': clsint, 'name': rest}
        return labels

    def mapclasses(self, classes, objects, verbs):
        with open('../models/charades/Charades_v1_mapping.txt') as f:
            for line in f:
                x = line.split(' ')
                cls = x[0]
                obj = x[1]
                vrb = x[2]
                clsint = int(cls[1:])
                objint = int(obj[1:])
                verbint = int(vrb[1:])
                classes[clsint]['obj'] = {'id': objint, 'name': objects[objint]['name']}
                classes[clsint]['verb'] = {'id': verbint, 'name': verbs[verbint]['name']}

    def prepare_im(self, image_np):
        # Normalize image and fix dimensions
        image_np = cv2.resize(image_np, dsize=(224, 224)).astype(np.float32) / 255.0
        mean = np.array([0.485, 0.456, 0.406])
        std = np.array([0.229, 0.224, 0.225])
        image_np = (image_np - mean) / std

        # Expand dimensions since the model expects images to have shape: [1, None, None, 3]
        image_np_expanded = np.expand_dims(image_np, axis=0)
        return image_np_expanded

    def recognize_activity(self, image_np, sess, detection_graph, accumulator):
        image_np_expanded = self.prepare_im(image_np)
        image_tensor = detection_graph.get_tensor_by_name('input_image:0')
        classes = detection_graph.get_tensor_by_name('classifier/Reshape:0')

        # Actual detection.
        (classes) = sess.run(
            [classes],
            feed_dict={image_tensor: image_np_expanded})

        classes = np.exp(np.squeeze(classes))
        classes = classes / np.sum(classes)
        accumulator[:] = PREDICTION_DECAY * accumulator[:] + (1 - PREDICTION_DECAY) * classes
        classes = np.argsort(accumulator)[::-1][:3]

        print('[VIDEO]:', self.category_classes[classes[0]])

        return str(self.category_classes[classes[0]]['name'])
