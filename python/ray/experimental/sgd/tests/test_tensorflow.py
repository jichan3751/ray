from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import os
import pytest
import tempfile
import numpy as np

from ray import tune
from ray.tests.conftest import ray_start_2_cpus  # noqa: F401
from ray.experimental.sgd.tensorflow import (TensorFlowTrainer,
                                             TensorFlowTrainable)

from ray.experimental.sgd.examples.tensorflow_train_example import (
    simple_model, simple_dataset)


@pytest.mark.parametrize(  # noqa: F811
    "num_replicas", [1, 2])
def test_train(ray_start_2_cpus, num_replicas):  # noqa: F811
    trainer = TensorFlowTrainer(
        model_creator=simple_model,
        data_creator=simple_dataset,
        num_replicas=num_replicas,
        batch_size=128)

    train_stats1 = trainer.train()
    train_stats1.update(trainer.validate())
    print(train_stats1)

    train_stats2 = trainer.train()
    train_stats2.update(trainer.validate())
    print(train_stats2)

    if "train_loss" in train_stats1 and "train_loss" in train_stats2:
        print(train_stats1["train_loss"], train_stats2["train_loss"])
        assert train_stats1["train_loss"] > train_stats2["train_loss"]

    print(
        train_stats1["validation_loss"],
        train_stats2["validation_loss"],
    )
    assert train_stats1["validation_loss"] > train_stats2["validation_loss"]


@pytest.mark.parametrize(  # noqa: F811
    "num_replicas", [1, 2])
def test_tune_train(ray_start_2_cpus, num_replicas):  # noqa: F811

    config = {
        "model_creator": tune.function(simple_model),
        "data_creator": tune.function(simple_dataset),
        "num_replicas": num_replicas,
        "use_gpu": False,
        "batch_size": 128
    }

    analysis = tune.run(
        TensorFlowTrainable,
        num_samples=2,
        config=config,
        stop={"training_iteration": 2},
        verbose=1)

    # checks loss decreasing for every trials
    for path, df in analysis.trial_dataframes.items():
        validation_loss1 = df.loc[0, "validation_loss"]
        validation_loss2 = df.loc[1, "validation_loss"]

        assert validation_loss2 <= validation_loss1


@pytest.mark.parametrize(  # noqa: F811
    "num_replicas", [1, 2])
def test_save_and_restore(ray_start_2_cpus, num_replicas):  # noqa: F811
    trainer1 = TensorFlowTrainer(
        model_creator=simple_model,
        data_creator=simple_dataset,
        num_replicas=num_replicas,
        batch_size=128)
    trainer1.train()

    filename = os.path.join(tempfile.mkdtemp(), "checkpoint")
    trainer1.save(filename)

    model1 = trainer1.get_model()
    trainer1.shutdown()

    trainer2 = TensorFlowTrainer(
        model_creator=simple_model,
        data_creator=simple_dataset,
        num_replicas=num_replicas,
        batch_size=128)
    trainer2.restore(filename)

    model2 = trainer2.get_model()
    trainer2.shutdown()

    os.remove(filename)

    model1_config = model1.get_config()
    model2_config = model2.get_config()
    assert _compare(model1_config, model2_config, skip_keys=["name"])

    model1_weights = model1.get_weights()
    model2_weights = model2.get_weights()
    assert _compare(model1_weights, model2_weights)

    model1_opt_weights = model1.optimizer.get_weights()
    model2_opt_weights = model2.optimizer.get_weights()
    assert _compare(model1_opt_weights, model2_opt_weights)


def _compare(d1, d2, skip_keys=None):
    """Compare two lists or dictionaries or array"""
    if type(d1) != type(d2):
        return False

    if isinstance(d1, dict):
        if set(d1) != set(d2):
            return False

        for key in d1:
            if skip_keys is not None and key in skip_keys:
                continue

            if not _compare(d1[key], d2[key], skip_keys=skip_keys):
                return False

    elif isinstance(d1, list):
        for i, _ in enumerate(d1):
            if not _compare(d1[i], d2[i], skip_keys=skip_keys):
                return False

    elif isinstance(d1, np.ndarray):
        if not np.array_equal(d1, d2):
            return False
    else:
        if d1 != d2:
            return False

    return True
