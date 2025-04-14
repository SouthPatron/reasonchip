#!/usr/bin/env bash


SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"


OUTPUT_DIR=${SCRIPT_DIR}/src/content/chipsets/
CHIPMENU_FILE=${SCRIPT_DIR}/src/layouts/partials/chip_menu.html
CHIPSET_TEMPLATE_FILE=${SCRIPT_DIR}/templates/chipset.j2

rm -rf ${OUTPUT_DIR}

${SCRIPT_DIR}/process_chipset.py					\
	--out-dir ${OUTPUT_DIR}							\
	--out-menu ${CHIPMENU_FILE}						\
	--chipset-template ${CHIPSET_TEMPLATE_FILE}


