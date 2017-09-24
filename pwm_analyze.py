#!/usr/bin/env python3

"""Given a stream of 0 and 1 bytes, analyze it as PWM messages."""

# Forgive the global variables. I find this easier than building a fake
# object to contain them.
run_state = 0
run_duration = 0
run_starttime = 0
msg_state = 0


def process_message_bit(bit, t):
    """Process a single message symbol.

    bit -- the symbol value, 0 or 1
    t -- the number of samples into the file where the symbol started

    This function prints out t at the beginning of a message, and then
    prints the 0 or 1 value of the symbol, thus building up a message
    line that looks like this:
      1234: 0101010101010101010101010101

    This function doesn't terminate the output line; that's left to
    complete_message().
    """
    global msg_state

    if msg_state == 0:
        msg_state = 1
        print("%6d: " % t, end="")
    print("%d" % bit, end="")


def reset_message(t):
    """Reset the message processing machine, for error recovery."""
    global msg_state

    print("\nResetting message processing at %d" % t)
    msg_state = 0


def complete_message(t):
    """Process the normal end of a message."""
    global msg_state

    print("")
    msg_state = 0


def new_burst(t):
    """Process the end of a burst of messages. Just output a blank line."""
    print("")


def process_run(run_value, duration, t):
    """Process a run of samples that were all 0 or all 1

    run_value -- the sample value that was held during this run, 0 or 1
    duration -- the number of samples for which the value was held
    t -- the number of samples into the file where the run started

    We expect runs of the value 1 that last for about 2 or about 6 samples,
    and runs of the value 0 that are 2, 6, 60, or many more samples long.
    Runs of 60 separate messages within a burst, and longer runs separate
    different bursts. All the counts are given some tolerance since the
    sampling is asynchronous.

    When we process a run of value 1, we transcode it from its sample value
    (1 in this case) to a symbol value of 0 for a short run or 1 for a long
    run, and pass the symbol value up to process_message_bit().
    """
    # print("%d for %d samples" % (run_value,duration))
    if duration <= 3:
        if run_value == 1:
            process_message_bit(0, t)
    elif duration <= 8:
        if run_value == 1:
            process_message_bit(1, t)
    elif duration <= 58:
        reset_message(t)
    elif duration <= 63 and run_value == 0:
        complete_message(t)
    elif run_value != 0:
        reset_message(t)
    else:
        complete_message(t)
        new_burst(t)


def process_sample(sample, time):
    """Process a single sample from the input file.

    sample -- the value of the sample, 0x00 (no signal) or 0x01 (signal)
    time -- the number of samples into the file where the sample occurred

    This function just gathers the samples up into runs of the same value
    and passed them up to process_run().
    """
    global run_state, run_duration, run_starttime

    if sample == b'\00':
        if run_state == 0:
            run_duration += 1
        else:
            process_run(1, run_duration, run_starttime)
            run_duration = 1
            run_state = 0
            run_starttime = time
    elif sample == b'\01':
        if run_state == 1:
            run_duration += 1
        else:
            process_run(0, run_duration, run_starttime)
            run_duration = 1
            run_state = 1
            run_starttime = time
    else:
        print("sample not understood")

# Read the file byte by byte and process the bytes as samples.
t = 0
with open("blet_ook.out", "rb") as f:
    while True:
        sample = f.read(1)
        if not sample:
            process_run(run_state, run_duration, run_starttime)
            break
        process_sample(sample, t)
        t += 1
