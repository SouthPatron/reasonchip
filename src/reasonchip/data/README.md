# Data Files

## Overview

This directory contains data files that are packaged with the Python
application. These files are used as static resources and are not
processed or transformed by the code.

## Filesystem Overview

| Location | Description                                |
| -------- | ------------------------------------------|
| [raw_data/](./raw_data/) | Contains original input datasets         |
| [reference/](./reference/) | Includes reference data for validation   |

## Onboarding Approach

Start by reviewing usage instances of these data files within the
application codebase to understand their role. Familiarity with data
format standards used in the files (e.g. CSV, JSON) is essential.
These files typically represent the fixed inputs or lookup tables
that the software relies on during execution.

Understand how the files are loaded and consumed through the
application layers to grasp their influence on processing workflows.

## Additional Notes

- These files are treated as static assets and should not be modified
  during runtime.
- Updates to these files require appropriate data validation and
  version control considerations to maintain package stability.
