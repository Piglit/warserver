
all: server client
	@echo "done"

server:
	pip3 install -r requirements.txt
	@echo "server ok"

client:
	ldconfig -p |grep bier > /dev/null
	pip3 install -r requirements_client.txt
	@echo "client ok"



.PHONY: servver, client, all

