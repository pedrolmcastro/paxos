
import paxos

def propose_value(messenger, value):
    """Proposes a value to the system.

    Args:
        messenger: A Messenger object.
        value: The value to propose.

    Returns:
        True if the value was proposed successfully, False otherwise.
    """
    print(f'Proposing value: {value}')
    proposer = paxos.Proposer(messenger, value)
    try:
        proposer.propose()
        return True
    except:
        return False


def get_accepted_value(messenger):
    """Gets the accepted value from the system.

    Args:
        messenger: A Messenger object.

    Returns:
        The accepted value, or None if there is no accepted value yet.
    """
    
    learner = paxos.Learner(messenger)
    accepted_value = learner.receive()
    if accepted_value is not None:
        print(f'Accepted value: {accepted_value}')
        return accepted_value['value']
    else:
        return None
    
def approve_or_reject_value(messenger, proposal_number, value):
    """Approves or rejects a proposed value.

    Args:
        messenger: A Messenger object.
        proposal_number: The proposal number of the value to be approved or rejected.
        value: The value to be approved or rejected.

    Returns:
        True if the value was approved, False otherwise.
    """

    acceptor = paxos.Acceptor(messenger)
    try:
        acceptor.receive()
        if proposal_number > acceptor.promised_proposal_number:
            acceptor.promised_proposal_number = proposal_number
            acceptor.send_promise_message(proposal_number, value)
        elif proposal_number >= acceptor.promised_proposal_number:
            acceptor.accepted_proposal_number = proposal_number
            acceptor.accepted_value = value
            acceptor.send_accepted_message(proposal_number)
            print(f'Accepted')
        return True
    except:
        return False
    
#  Exemplos de uso:
#Proposer############
# Create a Messenger object.
#messenger = paxos.Messenger(["localhost:8080"])

# Propose a value.
#
# success = propose_value(messenger, "Hello, world!")

# If the value was proposed successfully, wait for it to be accepted.
#if success:
#    accepted_value = get_accepted_value(messenger)

# Do something with the accepted value.
#print(accepted_value)


#Acceptor####################
# Create a Messenger object.
#messenger = paxos.Messenger(["localhost:8080"])

# Receive a proposed value.
#proposal_number, value = messenger.receive()

# Approve or reject the proposed value.
#success = approve_or_reject_value(messenger, proposal_number, value)

# If the value was approved successfully, send an accepted message.
#if success:
#    messenger.send_accepted_message(proposal_number)