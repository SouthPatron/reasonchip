#!/usr/bin/env bash


#	--log-level reasonchip.cli.commands.serve=DEBUG			\

reasonchip dispatch							\
	--log-level DEBUG						\
	--amqp-url ${AMQP_URL}					\
	--amqp-topic reasonchip					\
	--variables ./variables.json			\
	--set "a.b.e=6"							\
	chatbot.app.entry

