#!/usr/bin/env bash

reasonchip run								\
	--log-level DEBUG						\
	--collection chatbot=./workflows		\
	chatbot.app.entry
