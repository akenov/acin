import keras
import random
import numpy as np
# import sklearn
from numpy import matlib
from sklearn.utils import shuffle


class ChndDataGenerator(keras.utils.Sequence):
    """Generates data for Keras"""
    def __init__(self, name_, type_, batch_size, dim, list_idxes, aug_types, batch_factor_):
        """Initialization"""
        self.name = name_
        self.type = type_
        # self.batch_size = int(batch_size / len(aug_types))
        self.batch_size = int(batch_size / batch_factor_**2)
        self.dim = dim
        self.list_idxes = list_idxes
        self.aug_types = aug_types
        self.train_data = np.load(self.name + '.' + self.type + '.data.npy')
        self.train_labels = np.load(self.name + '.' + self.type + '.labels.npy')
        self.train_data, self.train_labels = shuffle(self.train_data, self.train_labels)
        self.sigma = (0.1 / 4)
        self.batch_factor = batch_factor_

    def __getitem__(self, index):
        """Generate one batch of data"""
        # Generate indexes of the batch
        indexes = self.list_idxes[index*self.batch_size:(index+1)*self.batch_size]

        #print("Processing batch #%d" % index)
        #print(indexes)
        # Generate data
        x, y = self.__data_generation(indexes)

        #print(" %s getitem() returns x in %s and y in %s " % (self.type, (x.shape, ), (y.shape, )))
        #print("y dist: {}".format(np.sum(y, axis=0)))
        return x, y

    def on_epoch_end(self):
        #"""Updates indexes after each epoch"""
        #print("Epochs end.")
        self.train_data, self.train_labels = shuffle(self.train_data, self.train_labels)

    def __len__(self):
        """Denotes the number of batches per epoch"""
        #print("LEN method called %s " % self.type)
        # return int(np.floor(len(self.list_idxes) / (self.batch_size * len(self.aug_types))))
        return int(np.floor(len(self.list_idxes) / (self.batch_size ))* self.batch_factor**2)

    @staticmethod
    def scale_augmentation(odata):
        # print("Doing data scale augmentation.")
        fa_scale = 1 + (random.randrange(-30, 30, 1) / 100)  # uniform distribution
        # print("Scale factor: %.2f" % fa_scale)
        data_aug = np.multiply(odata, fa_scale)
        return data_aug

    def shift_augmentation(self, odata):
        # print("Doing data shift augmentation.")
        data_aug = np.zeros(odata.shape)
        for seq in range(self.batch_size):
            sequence = odata[seq, :, :, :]
            clean_width = int(sequence[~np.all(sequence == 0.0, axis=3)].shape[0]/sequence.shape[2])
            sequence_clean = sequence[~np.all(sequence == 0.0, axis=3)]\
                .reshape([clean_width, sequence.shape[2], sequence.shape[3]])
            shift_x_fac = random.gauss(mu=0, sigma=self.sigma)  # Nunez
            shift_y_fac = random.gauss(mu=0, sigma=self.sigma)  # Nunez
            # Do the shift augmentation
            shift_vec = np.array([[shift_x_fac, shift_y_fac, 0]])
            shift = matlib.repmat(shift_vec, int(sequence_clean.shape[0]*sequence_clean.shape[1]), 1)\
                .reshape(sequence_clean.shape)
            sequence_shifted = sequence_clean + shift
            data_aug[seq, :, :, :] = np.pad(sequence_shifted, [(0, odata.shape[1] - clean_width), (0, 0), (0, 0)],
                                            mode='constant', constant_values=0)
        return data_aug

    def noise_augmentation(self, odata):
        max_width = self.dim[1]
        # print("Doing data noise augmentation.")
        data_aug = np.zeros([odata.shape[0], odata.shape[1], odata.shape[2], odata.shape[3]])
        num_seqncs = odata.shape[0]
        # print("num_frames %s " % num_frames)
        num_joints = odata.shape[1]
        joints_total = random.randint(1, 4)  # random num of joints to augment
        joints_range = list(np.arange(0, num_joints, 1))
        noise_joints = []
        for x in np.arange(joints_total):
            id_j = random.choice(joints_range)
            noise_joints.append(id_j)
            joints_range.remove(id_j)
        # print(noise_joints)
        for seq in range(num_seqncs):
            for jnt in range(num_joints):
                if jnt in noise_joints:
                    noise_factors = np.ones([max_width, 3])
                    noise_factors[:, 0] = noise_factors[:, 0] * random.gauss(mu=0, sigma=self.sigma)  # Nunez
                    noise_factors[:, 1] = noise_factors[:, 1] * random.gauss(mu=0, sigma=self.sigma)  # Nunez
                    noise_factors[:, 2] = noise_factors[:, 2] * random.gauss(mu=0, sigma=self.sigma)  # Nunez
                    data_aug[seq, :, jnt, :] = odata[seq, :, jnt, :] + noise_factors
                    # print("Noise factors: ")
                    # print(noise_factors)
                else:
                    data_aug[seq, :, jnt, :] = odata[seq, :, jnt, :]
        return data_aug

    @staticmethod
    def subsample_augmentation(odata):
        # print("Doing data subsample augmentation.")
        data_aug = np.zeros([odata.shape[0], odata.shape[1], odata.shape[2], odata.shape[3]])
        num_seqncs = odata.shape[0]
        num_frames = odata.shape[1]
        # Alternative go with all possible combination would be for displmt in (2,3,4) and for step in (2,3)
        # better generate more random epochs? #17.10.2018
        for seq in range(num_seqncs):
            displmt = random.randint(2, 4)  # random displacement to sequal (2, 3, 4)
            step = random.randint(2, 3)  # random step to iterate (2, 3)
            # print("Subsample %displmt random numbers displmt = %displmt, step = %displmt" % (f,displmt,step))
            for frm, frm_new in zip(range(displmt, num_frames, step), range(num_frames)):
                data_aug[seq, frm_new, :, :] = odata[seq, frm, :, :]
        return data_aug

    @staticmethod
    def interpolate_augmentation(odata):
        # print("Doing time interpolation data augmentation")
        data_aug = np.zeros([odata.shape[0], odata.shape[1], odata.shape[2], odata.shape[3]])
        num_seqncs = odata.shape[0]
        num_frames = odata.shape[1]
        num_joints = odata.shape[2]
        for seq in range(num_seqncs):
            r = random.randint(20, 80) / 100
            # print("Random scaling factor: %f" % r)
            for frm in range(num_frames-1):
                for jnt in range(num_joints):
                    # print("Current coordinate values: %s " % odata[seq, frm, jnt, :])
                    # print("Next  coordinate values: %s " % odata[seq, int(frm + 1), jnt, :])
                    frm_prev = odata[seq, frm, jnt, :]
                    frm_next = odata[seq, frm + 1, jnt, :]
                    if (frm_prev == 0.0).all() and (frm_next == 0.0).all():
                        # print("Interpolation break - padding reached")
                        break
                    frm_step = np.subtract(frm_next, frm_prev)
                    data_aug[seq, frm + 1, jnt, :] = np.add(frm_prev, np.multiply(frm_step, r))
                    # print("Interpolated coordinate value: %s " % data_aug[seq, int(frm + 1), jnt, :])
        return data_aug

    def chain_shift_augmentation(self, odata):
        # print("Doing data shift augmentation.")
        data_aug = np.zeros(odata.shape)
        sequence = odata
        clean_width = int(sequence[~np.all(sequence == 0.0, axis=3)].shape[0]/sequence.shape[2])
        sequence_clean = sequence[~np.all(sequence == 0.0, axis=3)] \
            .reshape([clean_width, sequence.shape[2], sequence.shape[3]])
        shift_x_fac = random.gauss(mu=0, sigma=self.sigma)  # Nunez
        shift_y_fac = random.gauss(mu=0, sigma=self.sigma)  # Nunez
        # Do the shift augmentation
        shift_vec = np.array([[shift_x_fac, shift_y_fac, 0]])
        shift = matlib.repmat(shift_vec, int(sequence_clean.shape[0]*sequence_clean.shape[1]), 1) \
            .reshape(sequence_clean.shape)
        sequence_shifted = sequence_clean + shift
        data_aug[0, :, :, :] = np.pad(sequence_shifted, [(0, odata.shape[1] - clean_width), (0, 0), (0, 0)],
                                        mode='constant', constant_values=0)
        return data_aug

    def __augment_data(self, augtype, odata):
        if augtype == 'none':
            return odata
        elif augtype == 'scale':
            scaled = self.scale_augmentation(odata)
            return scaled
        elif augtype == 'shift':
            shifted = self.shift_augmentation(odata)
            return shifted
        elif augtype == 'noise':
            noised = self.noise_augmentation(odata)
            return noised
        elif augtype == 'subsample':
            subsampled = self.subsample_augmentation(odata)
            return subsampled
        elif augtype == 'interpol':
            interpolated = self.interpolate_augmentation(odata)
            return interpolated
        elif augtype == 'scale_shift':
            scaled = self.scale_augmentation(odata)
            shifted_scaled = self.shift_augmentation(scaled)
            return shifted_scaled
        elif augtype == 'ITP_SCL_SFT':
            interpolated = self.interpolate_augmentation(odata)
            scaled = self.scale_augmentation(interpolated)
            return self.shift_augmentation(scaled)
        elif augtype == 'chain_shift':
            shifted = self.chain_shift_augmentation(odata)
            return shifted
        else:
            return odata

    def __data_generation(self, idxes):
        # print("Calling data_generation()")
        augmentations = self.aug_types

        train_data = self.train_data[idxes]
        # print(train_data.shape)
        train_labels = self.train_labels[idxes]

        # Generate augmentation data
        agmnt_data = []
        agmnt_labels = []

        # for agmt_type in augmentations:
        #     sppl_data = self.__augment_data(agmt_type, train_data)
        #     aug_data, aug_labels = shuffle(sppl_data, train_labels, random_state=42)
        #     agmnt_data.append(aug_data)
        #     agmnt_labels.append(aug_labels)

        # simple & suboptimal try to chain scale and shift, w/o implementing recursion method for now
        for sid in range(train_data.shape[0]):
            sample = train_data[sid, :, :, :].reshape([1, self.dim[0], self.dim[1], self.dim[2]])
            label = train_labels[0, :].reshape([1, -1])
            for id_sc in range(self.batch_factor):
                scaled = self.__augment_data("scale", sample)
                for id_sft in range(self.batch_factor):
                    shifted_scaled = self.__augment_data("chain_shift", scaled)
                    agmnt_data.append(shifted_scaled)
                    agmnt_labels.append(label)

        batch_data = np.asarray(agmnt_data).reshape(-1, train_data.shape[1], train_data.shape[2], train_data.shape[3])
        batch_labels = np.asarray(agmnt_labels).reshape(-1, train_labels.shape[1])
        # Shuffle the whole batch before returning
        batch_data_fin, batch_labels_fin = shuffle(batch_data, batch_labels)
        # print("dataGen() returns batch_data of %s and batch_labels of %s " % \
        # ((batch_data_fin.shape, ), (batch_labels_fin.shape, )))
        return batch_data_fin, batch_labels_fin
