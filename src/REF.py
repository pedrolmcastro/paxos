class Messenger:
    def __init__(self, nodes):
        self.nodes = nodes

    def send(self, message, to):
        #BROADCASTS MESSAGE
        pass

    def receive(self):
        #RECIEVES MESSAGE
        pass


class Proposer:
    def __init__(self, messenger, value):
        self.messenger = messenger
        self.value = value
        self.proposal_number = 0

    def propose(self):
        self.proposal_number += 1
        message = {'type': 'prepare', 'proposal_number': self.proposal_number}
        self.messenger.send(message, self.messenger.nodes)
        promises = []
        while len(promises) < len(self.messenger.nodes):
            message = self.messenger.receive()
            if message['type'] == 'promise':
                promises.append(message)
        max_proposal_number = 0
        max_value = None
        for promise in promises:
            if promise['proposal_number'] > max_proposal_number:
                max_proposal_number = promise['proposal_number']
                max_value = promise['value']
        if max_value is None:
            max_value = self.value
        message = {'type': 'accept', 'proposal_number': self.proposal_number, 'value': max_value}
        self.messenger.send(message, self.messenger.nodes)


class Acceptor:
    def __init__(self, messenger):
        self.messenger = messenger
        self.promised_proposal_number = None
        self.accepted_proposal_number = None
        self.accepted_value = None

    def receive(self):
        message = self.messenger.receive()
        if message['type'] == 'prepare':
            if self.promised_proposal_number is None or message['proposal_number'] > self.promised_proposal_number:
                self.promised_proposal_number = message['proposal_number']
                message = {'type': 'promise', 'proposal_number': self.promised_proposal_number, 'value': self.accepted_value}
                self.messenger.send(message, [message['from']])
        elif message['type'] == 'accept':
            if self.promised_proposal_number is None or message['proposal_number'] >= self.promised_proposal_number:
                self.promised_proposal_number = message['proposal_number']
                self.accepted_proposal_number = message['proposal_number']
                self.accepted_value = message['value']
                message = {'type': 'accepted', 'proposal_number': self.accepted_proposal_number}
                self.messenger.send(message, self.messenger.nodes)


class Learner:
    def __init__(self, messenger):
        self.messenger = messenger
        self.accepted_proposal_numbers = []
        self.accepted_values = []

    def receive(self):
        message = self.messenger.receive()
        if message['type'] == 'accepted':
            self.accepted_proposal_numbers.append(message['proposal_number'])
            if message['proposal_number'] not in self.accepted_proposal_numbers:
                self.accepted_values.append(message['value'])
                
                
        