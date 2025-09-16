# **************************************************************************** #
#                                                                              #
#                                                         :::      ::::::::    #
#    Makefile                                           :+:      :+:    :+:    #
#                                                     +:+ +:+         +:+      #
#    By: luzog78 <luzog78@gmail.com>                +#+  +:+       +#+         #
#                                                 +#+#+#+#+#+   +#+            #
#    Created: 2025/08/14 11:18:35 by luzog78           #+#    #+#              #
#    Updated: 2025/09/16 02:49:17 by luzog78          ###   ########.fr        #
#                                                                              #
# **************************************************************************** #

NAME		= Forty420
MAIN		= app/main.py

PYTHON		= python3
VENV		= .venv

ENV_PROD	= .env
ENV_DEV		= .dev.env
ENV_SECRET	= secrets.txt

LOGS_ACCESS	= ./logs/gunicorn.access.log
LOGS_ERROR	= ./logs/gunicorn.out.log
LOGS_MAIN	= ./logs/gunicorn.main.log
PID_FILE	= ./logs/gunicorn.pid


all: $(NAME)


init: $(VENV)/bin/python
	$(VENV)/bin/pip install -r requirements.txt


$(VENV)/bin/python:
	$(PYTHON) -m venv $(VENV)


$(NAME): $(MAIN) init stop
	mkdir -p $$(dirname $(LOGS_ACCESS)) $$(dirname $(LOGS_ERROR)) $$(dirname $(LOGS_MAIN)) $$(dirname $(PID_FILE))
	export $$(grep -v '^#' $(ENV_PROD) | sed -e 's/^\([^=\t\r ]\+\)\s\+=\s\+/\1=/g' | xargs) \
	export $$(grep -v '^#' $(ENV_SECRET) | sed -e 's/^\([^=\t\r ]\+\)\s\+=\s\+/\1=/g' | xargs) \
	&& nohup $(VENV)/bin/python -m gunicorn \
		--bind 0.0.0.0:$${PORT:-5000} \
		--workers $${WORKERS:-1} \
		--pid $(PID_FILE) \
		--access-logfile $(LOGS_ACCESS) \
		--error-logfile $(LOGS_ERROR) \
		--access-logformat '%(t)s %(p)s %(h)s %(u)s %(s)s %(m)s "%(U)s%(q)s" %(B)s %(M)s "%({Authorization}i)s" "%(f)s" "%(a)s"' \
		--capture-output \
		--pythonpath "$$(dirname "$(MAIN)")" \
		"$$(basename "$(MAIN)" .py):app" \
		> $(LOGS_MAIN) 2>&1 &


stop:
	@if [ -f $(PID_FILE) ]; then \
		PID=$$(cat $(PID_FILE)); \
		if kill -0 $$PID > /dev/null 2>&1; then \
			echo "Stopping $(NAME) (PID: $$PID)..."; \
			kill $$PID; \
		else \
			echo "$(NAME) is not running."; \
		fi; \
		rm -f $(PID_FILE); \
	else \
		echo "$(NAME) is not running."; \
	fi


dev: $(MAIN) init
	$(VENV)/bin/python $(MAIN) $(ENV_PROD) $(ENV_SECRET) $(ENV_DEV)


clean:
	rm -rf $(VENV)
	find . \( -type d -name "__pycache__" -o -type f -name "*.pyc" \) -exec rm -rf {} +


re: stop clean all


.PHONY: all init stop dev clean re
