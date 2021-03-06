from os.path import isfile, join, exists
from os import listdir, makedirs
import numpy as np
from datetime import datetime

import collections
import random


class PreProcess:

    ##################################################
    # Stock Data Pre Process
    ##################################################
    @staticmethod
    def make_sequence_data(input_path, output_path, sequence_length):
        """
        This will make sequence_length data with label stored data

        :param input_path:
        :param output_path:
        :param sequence_length:
        :param normalize:
        :param label_range:
        :return:
        """

        a = datetime.now()
        data_list = sorted([f.replace('.npy', '') for f in listdir(input_path)
                            if isfile(join(input_path, f)) and '.DS_Store' not in f])

        all_sequence_data = list()
        all_end_data = list()

        for fname in data_list:

            sequence_data = list()
            end_data = list()

            values = np.load(join(input_path, fname + '.npy'))

            for d in values:
                d[0] = int(d[0].replace('.', ''))
                for i in range(1, len(d)):
                    d[i] = int(d[i])

            values = sorted(values, key=lambda t: t[0])

            # add prior day feature

            # add key as feature

            # Make sets of data in sequence_length

            for pos in range(len(values)):
                if pos + sequence_length >= len(values):
                    # print('pos + sequence_length: %i and len(values): %i' % (pos + sequence_length, len(values)))
                    break

                # Values of length of sequence
                v = values[pos: pos + sequence_length]
                e = values[pos + sequence_length]
                sequence_data.append(v)
                end_data.append(e)

            all_sequence_data.extend(sequence_data)
            all_end_data.extend(end_data)

            if output_path is not None:
                n_output_path = join(output_path, 'sequence_data')
                if not exists(n_output_path):
                    makedirs(n_output_path)
                np.save(join(n_output_path, fname), [sequence_data, end_data])

        a = datetime.now() - a
        print('Elapsed time:', a)

        return all_sequence_data, all_end_data

    @staticmethod
    def make_dataset(sequence_data, end_data, output_path, label_price, label_term, mode, normalize, label_dict=dict()):
        """
        Make labels related to the given sequence data

        :param sequence_data:
        :param end_data:
        :param output_path:
        :param label_price:
        :param label_term:
        :return:
        """

        a = datetime.now()

        queries = list()
        labels = list()

        # date, final_price, compare_to_prior, start_price, highest_price, lowest_price, num_of_traded
        # Added Features: None yet
        # Label:
        for seq_data, e_data in zip(sequence_data, end_data):
            v = list()
            # print(len(v))
            v.extend(seq_data)
            v.append(e_data)

            # print(len(v))
            l = list()
            for idx, value in enumerate(v):
                if idx == len(v) - 1:  # length 21 means idx 20, so when idx == 19 is the last one can be compared
                    break
                else:
                    r = int(float(
                        v[idx + 1][1] * 100 / v[idx][1]) - 100)  # Increase/decrease in ratio compare to d and d+1

                lf = -1
                for idx2, label in label_dict.items():
                    if label[0] <= r < label[1]:
                        lf = idx2
                        l.append(lf)
                        break

                if lf == -1:  # Not found in proper range
                    break

            if len(l) != len(seq_data):
                continue

            if normalize:
                seq_data = PreProcess.min_max_scaler(seq_data)

            queries.append(seq_data)
            labels.append(l)

        queries = np.array(queries)
        labels = np.array(labels)

        if mode == 2:
            labels = labels[:, -1]
            # print(labels[:10])
            # labels = np.reshape(labels, len(labels))
            # print(labels[:10])

            # 1d to 2d array
            labels = [[a] for a in labels]
            labels = np.array(labels)

        max_data_length = 100000

        if output_path is not None:
            for idx, pos in enumerate(range(0, len(queries), max_data_length)):
                result = dict()
                result['queries'] = queries[pos: min(pos + max_data_length, len(queries))]
                result['labels'] = labels[pos: min(pos + max_data_length, len(queries))]
                print('Data sequence created. saving now...')
                try:

                    n_output_path = join(output_path, 'labelled_data_' + str(mode))
                    if not exists(n_output_path):
                        makedirs(n_output_path)
                    np.save(join(n_output_path, 'x_y' + str(idx)), result)
                    print('Saving path: ', n_output_path)
                    # np.save(join(n_output_path, 'x'), queries)
                    # np.save(join(n_output_path, 'y'), labels)
                except Exception as e:
                    print('Saving Error!')
                    print(e)

        # a = datetime.now() - a
        # print('Elapsed time:', a)
        return queries, labels

    @staticmethod
    def min_max_scaler(data):
        ''' Min Max Normalization
        Parameters
        ----------
        data : numpy.ndarray
            input data to be normalized
            shape: [Batch size, dimension]
        Returns
        ----------
        data : numpy.ndarry
            normalized data
            shape: [Batch size, dimension]
        References
        ----------
        .. [1] http://sebastianraschka.com/Articles/2014_about_feature_scaling.html
        '''
        numerator = data - np.min(data, 0)
        denominator = np.max(data, 0) - np.min(data, 0)
        # noise term prevents the zero division
        return numerator / (denominator + 1e-7)

    ##################################################
    # NLP Pre Process
    ##################################################
    @staticmethod
    def build_dictionary(words, vocabulary_size):
        # Step 2: dictionary를 만들고 UNK 토큰을 이용해서 rare words를 교체(replace)한다.
        # N개 이하 데이터는 Unknown으로 변환 및 카운트 -> 개수가 큰 순서부터 단어:인덱싱
        # -> 인덱싱:단어 리턴 (reverse_dictionary가 reverse ordered dict역할)

        count = [['UNK', -1]]
        count.extend(collections.Counter(words).most_common(vocabulary_size - 1))
        dictionary = dict()
        for word, _ in count:
            dictionary[word] = len(dictionary)
        data = list()
        unk_count = 0
        for word in words:
            if word in dictionary:
                index = dictionary[word]
            else:
                index = 0  # dictionary['UNK']
                unk_count += 1
            data.append(index)
        count[0][1] = unk_count
        reverse_dictionary = dict(zip(dictionary.values(), dictionary.keys()))
        return data, count, dictionary, reverse_dictionary

    @staticmethod
    def generate_batch(batch_size, num_skips, skip_window, data, data_index):
        # Step 3: skip-gram model을 위한 트레이닝 데이터(batch)를 생성하기 위한 함수.
        # global data_index
        assert batch_size % num_skips == 0
        assert num_skips <= 2 * skip_window
        batch = np.ndarray(shape=(batch_size), dtype=np.int32)
        labels = np.ndarray(shape=(batch_size, 1), dtype=np.int32)
        span = 2 * skip_window + 1  # [ skip_window target skip_window ]
        buffer = collections.deque(maxlen=span)
        for _ in range(span):
            buffer.append(data[data_index])
            data_index = (data_index + 1) % len(data)
        for i in range(batch_size // num_skips):
            target = skip_window  # target label at the center of the buffer
            targets_to_avoid = [skip_window]
            for j in range(num_skips):
                while target in targets_to_avoid:
                    target = random.randint(0, span - 1)
                targets_to_avoid.append(target)
                batch[i * num_skips + j] = buffer[skip_window]
                labels[i * num_skips + j, 0] = buffer[target]
            buffer.append(data[data_index])
            data_index = (data_index + 1) % len(data)
        return batch, labels, data_index
