#!/bin/bash

while true; do
    read -p "Enter a value (or type 'exit' to quit): " user_input
    if [[ "$user_input" == "exit" ]]; then
        echo "Exiting..."
        break
    fi


	reasonchip run-local		\
		-e entry				\
		--vars ./_params.yml	\
		--vars ./_secrets.yml	\
		--set secrets.openai.api_key=$OPENAI_API_KEY						\
		--set secrets.openai.org_id=$OPENAI_ORG_ID							\
		--set message="$user_input"

done

