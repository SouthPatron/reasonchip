#!/usr/bin/env bash

while true; do
	read -rp "You: " message

	if [[ "$message" == "quit" ]]; then
		echo "Exiting chatbot..."
		break
	fi

	reasonchip dispatch							\
		--log-level DEBUG						\
		--amqp-url ${AMQP_URL}					\
		--amqp-topic reasonchip					\
		--variables ./variables.json			\
		chatbot.app.entry						\
		--set "message=$message"

done
