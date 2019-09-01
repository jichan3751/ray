from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import argparse
from tensorflow.data import Dataset
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Dense
import numpy as np

import ray
from ray import tune
from ray.experimental.sgd.tf.tf_trainer import TFTrainer, TFTrainable

NUM_TRAIN_SAMPLES = 1000
NUM_TEST_SAMPLES = 400


def linear_dataset(a=2, b=5, size=1000):
    x = np.arange(0, 10, 10 / size, dtype=np.float32)
    y = a * x + b

    x = x.reshape((-1, 1))
    y = y.reshape((-1, 1))

    return x, y


def simple_dataset(batch_size=20):
    x_train, y_train = linear_dataset(size=NUM_TRAIN_SAMPLES)
    x_test, y_test = linear_dataset(size=NUM_TEST_SAMPLES)

    train_dataset = Dataset.from_tensor_slices((x_train, y_train))
    test_dataset = Dataset.from_tensor_slices((x_test, y_test))
    train_dataset = train_dataset.shuffle(NUM_TRAIN_SAMPLES).repeat().batch(
        batch_size)
    test_dataset = test_dataset.repeat().batch(batch_size)

    return train_dataset, test_dataset


def simple_model():
    model = Sequential([Dense(10, input_shape=(1, )), Dense(1)])

    model.compile(
        optimizer="sgd",
        loss="mean_squared_error",
        metrics=["mean_squared_error"])

    return model


def train_example(num_replicas=1, batch_size=128, use_gpu=False):
    trainer = TFTrainer(
        model_creator=simple_model,
        data_creator=simple_dataset,
        num_replicas=num_replicas,
        use_gpu=use_gpu,
        config={
            "verbose": True,
            "fit_config": {
                "steps_per_epoch": NUM_TRAIN_SAMPLES // batch_size
            },
            "evaluate_config": {
                "steps": NUM_TEST_SAMPLES // batch_size,
            }
        },
        batch_size=batch_size)

    train_stats1 = trainer.train()
    train_stats1.update(trainer.validate())
    print(train_stats1)

    train_stats2 = trainer.train()
    train_stats2.update(trainer.validate())
    print(train_stats2)

    val_stats = trainer.validate()
    print(val_stats)
    print("success!")


def tune_example(num_replicas=1, use_gpu=False):
    config = {
        "model_creator": tune.function(simple_model),
        "data_creator": tune.function(simple_dataset),
        "num_replicas": num_replicas,
        "use_gpu": use_gpu,
        "batch_size": 128
    }

    analysis = tune.run(
        TFTrainable,
        num_samples=2,
        config=config,
        stop={"training_iteration": 2},
        verbose=1)

    return analysis.get_best_config(metric="validation_loss", mode="min")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--redis-address",
        required=False,
        type=str,
        help="the address to use for Redis")
    parser.add_argument(
        "--num-replicas",
        "-n",
        type=int,
        default=1,
        help="Sets number of replicas for training.")
    parser.add_argument(
        "--use-gpu",
        action="store_true",
        default=False,
        help="Enables GPU training")
    parser.add_argument(
        "--tune", action="store_true", default=False, help="Tune training")

    args, _ = parser.parse_known_args()

    ray.init(redis_address=args.redis_address)

    if args.tune:
        tune_example(num_replicas=args.num_replicas, use_gpu=args.use_gpu)
    else:
        train_example(num_replicas=args.num_replicas, use_gpu=args.use_gpu)
