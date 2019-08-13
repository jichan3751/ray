from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import argparse
from ray import tune
from ray.experimental.sgd.tensorflow2.tensorflow2_trainer import TensorFlow2Trainer

from ray.experimental.sgd.tests.tensorflow2_utils import (
    model_creator, optimizer_creator, data_creator)

def train_example(num_replicas=1, use_gpu=False):

    trainer1 = TensorFlow2Trainer(
        model_creator,
        data_creator,
        optimizer_creator,
        num_replicas=num_replicas,
        use_gpu=use_gpu,
        batch_size=512)
    train_stats1 = trainer1.train()
    # print(train_stats)

    train_stats2 = trainer1.train()
    # print(train_stats)

    assert train_stats1["train_loss"] > train_stats2["train_loss"]

    trainer1.shutdown()
    print("success!")


# def tune_example(num_replicas=1, use_gpu=False):
#     config = {
#         "model_creator": tune.function(model_creator),
#         "data_creator": tune.function(data_creator),
#         "optimizer_creator": tune.function(optimizer_creator),
#         "num_replicas": num_replicas,
#         "use_gpu": use_gpu,
#         "batch_size": 512,
#     }

#     analysis = tune.run(
#         TensorFlow2Trainable,
#         num_samples=2,
#         config=config,
#         stop={"training_iteration": 2},
#         verbose=1)

#     return analysis.get_best_config(metric="validation_loss", mode="min")


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

    import ray

    ray.init(redis_address=args.redis_address)

    # if args.tune:
    #     tune_example(num_replicas=args.num_replicas, use_gpu=args.use_gpu)
    # else:
    #     train_example(num_replicas=args.num_replicas, use_gpu=args.use_gpu)

    train_example(num_replicas=1, use_gpu=False)
