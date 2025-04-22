# Data Augmentation Utilities

## Overview

This directory contains utilities and helpers for data augmentation,
especially focusing on augmenting textual data. It includes implementations
of various transformers, data structure utilities for efficient sampling,
and evaluation mechanisms.

## Filesystem Overview

| Location                                    | Description                                 |
| ------------------------------------------| -------------------------------------------|
| [backoff_sample.py](./backoff_sample.py)  | Implements backoff sampling technique      |
| [composable_transformer.py](./composable_transformer.py) | Provides composable transformers for chaining augmentations |
| [samplers.py](./samplers.py)              | Contains classes for weighted and random sampling data structures |
| [sibling_augmenters.py](./sibling_augmenters.py) | Defines augmenters that operate on sets of sibling examples |
| [similar_augmenters.py](./similar_augmenters.py) | Implements augmenters focused on similarity-based strategies |
| [util.py](./util.py)                      | Collection of utility functions supporting the augmenters |
| [value_eval.py](./value_eval.py)          | Supports evaluation of augmentation results based on value criteria |

## Onboarding Approach

Start with understanding the data augmentation design pattern employed here.
Focus first on the `composable_transformer.py` which provides the abstraction
for chaining augmentation transformers. This patterns allows flexible combination
of different augmentation strategies.

Next, review `samplers.py` to understand the underlying data structures supporting
random and weighted sampling for generating variations. Understanding the
data structure internals will clarify how sampling efficiency and backoff
mechanisms work.

Then, move to the augmenter implementations in `sibling_augmenters.py` and
`similar_augmenters.py` to see concrete uses of sampling and transformation.
These classes implement domain-specific augmentations using the primitives.

Refer to `backoff_sample.py` for an advanced sampling strategy utilizing backoff.
Finally, utilities and evaluation modules provide supporting and validation
functionalities.

Knowledge of probability distributions, data structures, and transformer
patterns in software is essential to grasp the full scope of the augmentation
pipeline.

## Sampling Structures

The sampler classes implement both weighted random sampling and uniform random
sampling with attention to efficiency and locality. These are central for
probabilistic augmentations.

## Composable Transformers

The composable transformers are key abstractions allowing augmentation components
to be chained, composed, and reused cleanly. This modularity enables combining
multiple augmentation rules in sequence or in parallel.

## Evaluation

The value evaluation module supports scoring and validating augmentation outcomes
against criteria, allowing feedback and control in augmentation pipelines.

