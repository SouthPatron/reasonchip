#!/usr/bin/env bash


#	--log-level reasonchip.cli.commands.serve=DEBUG			\
#	--variables ./variables.json			\
#	--set "a.b.e=6"							\

reasonchip dispatch							\
	--log-level DEBUG						\
	--amqp-url ${AMQP_URL}					\
	--amqp-topic reasonchip					\
	chatbot.app.entry

