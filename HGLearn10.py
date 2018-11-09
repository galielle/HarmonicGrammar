# Implementation of the Gradual Learning Algorithm for Harmonic Grammar for letter strokes
# Written by Gali Ellenblum
# Parts of this code adapted from Connor McLaughlin

import sys
#import re
import random
import datetime
import numpy as np
import os
import glob

if len(sys.argv) != 7:
    exit("usage: HGlearn9.py <EvalFilesDir> <ConstraintsFile> <TargetsFile> <iterations> <rate> <weight initialization - 0 (random) or 1 (uniform)>")

else:
    ### Define basic parameters and get initial input
    override = 1  # Change here to override = 0 to create a new logfile for each run
    eval_files_dir = sys.argv[1]
    constraints_file = sys.argv[2]
    targets_filename = sys.argv[3]
    iterations = int(sys.argv[4])
    rate = float(sys.argv[5])
    uni = int(sys.argv[6])  # 0 = random initialization of weights; 1 = initialize all weights to 1.

##########################

def main(eval_files_dir, constraints_file, targets_filename, iterations, rate, uni, override):
    eval_files_letters = get_eval_files(eval_files_dir)
    filenames = eval_files_letters[0]
    letters = eval_files_letters[1]
    n_letters = len(letters)
    print 'Found %d characters in the %s folder' % (n_letters, eval_files_dir)

    # Get the list of active constraints
    constraints = get_constraints(constraints_file)
    print 'Found %d active constraints in the %s file' % (len(constraints), constraints_file)

    ## Get data from user files
    # Get violations
    print 'Analyzing constraint violations...'
    grammar = {}
    for eval_filename in filenames:
        grammar = write_letter(eval_filename, constraints, grammar)
    print 'All done with constraint violations!\n'

    # Get targets
    data = get_data(targets_filename)
    print 'Found %d targets...\n' % (len(data))

    # Initialize weights
    weights = initialize_weights(uni, constraints)

    # Open a log file
    logf = create_log_file(override)

    sum_of_relative_frequencies = sum(int(datum[2]) for datum in data)

    # Evaluate the data and adjust the weights for n iterations
    print 'Looking for optimal weights...'
    final_result = adjust_weights(iterations, data, grammar, weights, rate, sum_of_relative_frequencies)

    full_success = write_summary(final_result, constraints, logf)
    letters_hg = find_failures(grammar, data, constraints, final_result, logf, full_success)
    logf.close()

    return(letters_hg)


###################################################
#           FUNCTIONS USED IN THIS SCRIPT         #
###################################################

# Initialize the weights
def initialize_weights(uni, constraints):
    weights = []
    if uni == 0:
        for c in constraints:
            weights.append(round(random.random(), 2))
    elif uni == 1:
        for c in constraints:
            weights.append(1.0)
    else:
        print 'UNI must be either 0 or 1'
        exit()
    return weights

# Get the targets
def get_data(targets_filename):
    if targets_filename[-3:] != 'txt':
        targets_filename = targets_filename + '.txt'
    targets_file = open(targets_filename, 'rU')
    data = []
    for line in targets_file.readlines():
        m = line.split()
        letter = m.pop(0).split('-')[1]
        target = m
        data.append((letter, target, len(target)))
    targets_file.close()
    return data

# Compute the harmony based on a given set of weights and violations
def harmony(violations, weights):
    harmony = 0.0
    for i in range(0, len(weights)):
        harmony -= weights[i] * float(violations[i])
    return harmony

# Optimize the weights based on a given input
def optimize(weights, grammar, pInput, n_targets):
    #optimal_harmony = None
    # optimal_harmony = harmony(grammar[pInput][optimal_output], weights)
    outputs = grammar[pInput].keys()
    # h = optimal_harmony
    h = [harmony(grammar[pInput][o], weights) for o in outputs]
    optimal_output = {}
    for t in range(n_targets):
        t_index = h.index(max(h))
        optimal_output[outputs[t_index]] = h[t_index]
        h[t_index] = -1000
    return optimal_output

# Choose a random data point to test next
def next_datum(data, sum_of_relative_frequencies):
    r = random.randint(1, sum_of_relative_frequencies)
    datum = (data[0][0], data[0][1])
    if r > int(data[0][2]):
        frequency_sum = int(data[0][2])
        for i in range(1, len(data)):
            if r <= int(data[i][2]) + frequency_sum:
                datum = (data[i][0], data[i][1])
                break
            else:
                frequency_sum += int(data[i][2])
    return datum

# Compute the change vector to modify the weights
def compute_change_vector(error, target, rate):
    v = []
    for i in range(0, len(error)):
        v.append(round((float(error[i]) * rate) - (float(target[i]) * rate), 1))
    return v

def add_vectors(source, change):
    v = []
    for i in range(0, len(source)):
        v.append(source[i] + float(change[i]))
    return v

# Check if a given input matches the output
def update(datum, grammar, weights, rate):
    pInput = datum[0]
    target = datum[1]
    output = optimize(weights, grammar, pInput, len(target))
    if output.keys() == target:
        #print "For letter %s output %s is the same as target %s" % (pInput, ', '.join(output.keys()), ', '.join(target))
        weights = weights
    else:
        fail = []
        t_h = [harmony(grammar[pInput][t], weights) for t in target]
        for o in output:
            o_h = output[o]
            for t in range(len(target)):
                if o_h >= t_h[t] and o != target[t]:
                    fail.append((o, target[t]))
                    print "For letter %s target %s has lower harmony (%s) than candidate %s (%s)" % (pInput, target[t], t_h[t], o, o_h)
        if len(fail) == 0:
            print "NO FAILURES FOUND"
            weights = weights
        else:
            pick_one = random.choice(fail)
            change_vector = compute_change_vector(grammar[pInput][pick_one[0]], grammar[pInput][pick_one[1]], rate)
            weights = add_vectors(weights, change_vector)
    return weights

# Evaluate the data on a given set of weights
def evaluate(weights, grammar, data):
    correct_count = 0
    for datum in data:
        targets = datum[1]
        output = optimize(weights, grammar, datum[0], len(targets)).keys()
        # print 'data:\t' + datum[0], datum[1] + '\tOUTPUT', output
        if output == targets:
            correct_count += len(targets)
    accuracy = float(correct_count) / sum(n for (_, _,n) in data)
    text = 'ACCURACY is\t%s\n' % (str(accuracy))
    # logf.write(text)
    return (accuracy)

# Adjust the weights
def adjust_weights(iterations, data, grammar, weights, rate, sum_of_relative_frequencies):
    # Evaluate the data on the initial grammar
    initial_grammar_text = 'INITIAL GRAMMAR:\t'
    for i in range(0, len(weights)):
        initial_grammar_text = initial_grammar_text + str('%.2f\t' % (weights[i]))
    initial_grammar_text = initial_grammar_text + '\n'
    print initial_grammar_text
    accuracy = evaluate(weights, grammar, data)
    max_accuracy = accuracy
    max_acc_iter = 0
    max_acc_wts = weights
    print 'ITERATION: 0'

    # Evaluate and adjust the weights for n iterations
    i = 1
    s = 1
    max_acc_s = 1
    while i <= iterations:
        if max_accuracy == 1:
            print '\nReached an accuracy of 1 after %d iterations (%d total samples)' % (max_acc_iter, s-1)
            break
        # Define when to stop if no solution was found
        elif s >= max(10*len(data), iterations) or s >= (max_acc_s + max(200, iterations)):
            print '\nMax accuracy first reached %d samples ago. Stopping now.' % (s - max_acc_s)
            break
        # Otherwise run until n iterations were completed
        else:
            w = update(next_datum(data, sum_of_relative_frequencies), grammar, weights, rate)
            if w != weights:
                weights = w
                text = 'CURRENT GRAMMAR:\t'
                for j in range(0, len(weights)):
                    text = text + str('%.2f\t' % (weights[j]))
                text = text + '\n'
                # logf.write(text)
                accuracy = evaluate(weights, grammar, data)
                if accuracy > max_accuracy:
                    max_accuracy = accuracy
                    max_acc_iter = i
                    max_acc_wts = weights
                    max_acc_s = s
                i += 1
                text = 'ITERATION: %d\tACCURACY: %s' % (i, str(accuracy))
                print text
            else:
                1 == 1
                #print 'No update, sampling again'
            s += 1
    return ([max_accuracy, max_acc_iter, max_acc_wts, initial_grammar_text, max_acc_s])

# Create a log file - override=0 will create a new log for each run. 1 will create a new log once a day.
def create_log_file(override):
    now = datetime.datetime.now()
    counter = 1
    base_lf = 'Log%d-%d-%d' % (now.year, now.month, now.day)
    log_filename = base_lf + '.txt'
    if override == 1:
        logf = open(log_filename, 'w')
    else:
        while os.path.isfile(log_filename):
            counter += 1
            base_lf = 'Log%d-%d-%d_%d' % (now.year, now.month, now.day, counter)
            log_filename = base_lf + '.txt'
        logf = open(log_filename, 'w')
    return (logf)

# Write the best weights, max accuracy, and number of iterations to a log file
def write_summary(final_result, constraints, logf):
    # Get the best weights
    max_accuracy = final_result[0]
    max_acc_iter = final_result[1]
    max_acc_wts = final_result[2]
    max_acc_s = final_result[4]

    # Print a summary of the maximum accuracy and the weights associated with it
    summary_text = '\nMax accuracy reached: %.2f\nMax accuracy first reached on iteration: %d (%d samples)\nGrammar for max accuracy:' % (max_accuracy, max_acc_iter, max_acc_s)
    logf.write(summary_text)
    print summary_text
    best_weights = ''
    constraint_text = ''
    for i in range(0, len(max_acc_wts)):
        best_weights = best_weights + str('%.2f\t' % (max_acc_wts[i]))
        constraint_text = constraint_text + str('%s\t') % (constraints[i])
    logf.write('Constraint:\t%s\n' % (constraint_text))
    logf.write('Weight:\t%s' % (best_weights))
    print best_weights

    # If max accuracy is 1, exit
    if max_accuracy == 1:
        return (1)
    else:
        return(0)

# Find and print which letters still fail after the specified number of iterations
def find_failures(grammar, data, constraints, final_result, logf, full_success):
    while True:
        show_harmony = raw_input('\nWould you like to see the harmony and ranking of targets? Y/N\n').upper()
        if show_harmony not in ('Y', 'N'):
            print "Sorry, I didn\'t get that... "
            continue
        else:
            break
    best_weights = final_result[2]
    log_header = '\n\nLetter\tTarget\tHarmony\tRank\tN Cands\tCandidates ranked higher than the target\n'
    logf.write(log_header)
    letters_hg = {}
    failed_letters = []
    for datum in data:
        letter = datum[0]
        target = datum[1]
        harmonies = {}
        candidates = grammar[letter].keys()
        # Get the harmonies for all the candidates
        cand_harmonies = [harmony(grammar[letter][cand], best_weights) for cand in candidates]
        for i in range(len(candidates)):
            harmonies[candidates[i]] = cand_harmonies[i]
        for t in target:
            failures = []
            rank = 1
            ranked_above = []
            t_h = harmonies[t]
            for cand in harmonies.keys():
                if harmonies[cand] > t_h:
                    ranked_above.append(cand)
                    rank += 1
            if show_harmony == 'Y':
                print 'For the letter %s: the target %s has a Harmony of %.2f. It ranks %d out of %d candidates' % (letter, t, t_h, rank, len(grammar[letter]))
            log_text = '%s\t%s\t%s\t%d\t%d\t' % (letter, t, t_h, rank, len(grammar[letter]))
            for cand in ranked_above:
                if cand not in target:
                    failures.append(cand)
            if len(failures) > 0:
                failed_letters.append((letter, t, failures))
            log_text = log_text + '\t'.join(failures)
            logf.write('%s\n' % (log_text))
            letters_hg[(letter, t)] = (round(t_h, 3), rank, failures)
    if full_success == 1:
        print '\nALL DONE!!\n'
    else:
        print "\n\nThe following %d targets did not rank highest:\n" % (len(failed_letters))
        for failure in failed_letters:
            text = "Letter: %s\tTarget: %s\tCandidates ranked higher than the target:\t%s" % (failure[0], failure[1], '\t'.join(failure[2]))
            print text
        print '\nALL DONE!!\n'
    return(letters_hg)

#######################################
# Functions needed to format the data #
#######################################

# Get the list of eval file names and the list of participating letters from the directory
def get_eval_files(eval_dir):
    eval_dir = eval_dir
    os.chdir(eval_dir)
    eval_files = []
    letters = []
    for file in glob.glob("Eval-*.txt"):
        eval_files.append(file)
        letters.append(file.split('-')[1])
    return [eval_files, letters]

# Get the constraints from user input
def get_constraints(constraints_filename):
    if constraints_filename[-3:] != 'txt':
        constraints_filename = constraints_filename + '.txt'
    const_path = os.path.isfile(constraints_filename)
    while not const_path:
        while True:
            CorN = raw_input(
                'Constraints file not found in %s.\nPress 1 to change directory or 2 to enter a new constraints filename: ')
            if CorN not in ('1', '2'):
                print "Sorry, I didn\'t get that..."
                continue
            else:
                break
        if CorN == '1':
            new_path = raw_input("Enter a new directory path: ")
            os.chdir(new_path)
            const_path = os.path.isfile(constraints_filename)
            continue
        elif CorN == '2':
            constraints_filename = raw_input('Enter a new constraints filename: ')
            if constraints_filename[-3:] != 'txt':
                constraints_filename = constraints_filename + '.txt'
            const_path = os.path.isfile(constraints_filename)
            continue
        else:
            break
    const_filename = constraints_filename
    const_file = open(const_filename, 'rU')
    const = const_file.readlines()
    constraints = []
    for line in const:
        if line.strip().split()[1] == '1':
            constraints.append(int(line.strip().split()[0]))
    const_file.close()
    return (constraints)

# Get the candidates of a given letter
def write_letter(input_filename, constraints, grammar):
    # The script takes an input Eval filename (e.g., Eval-A-uc.txt) as an argument
    get_input_file = open(input_filename, 'rU')
    input_file = get_input_file.readlines()
    get_input_file.close()

    # Extract the name of the letter from the filename
    letter = input_filename.split('-')[-2]

    # Extract the number of candidates, and get rid of some unused header rows
    header = input_file.pop(0)
    n_cands = int(header.strip().split()[2])
    temp = input_file.pop(0)
    temp = input_file.pop(0)
    temp = input_file.pop(0)
    grammar[letter] = {}

    # Format each candidate line to extract the candidate code, number, and violations
    for line in input_file:
        line = line.strip().split()
        cand_code = line[0]
        cand_num = line[2]
        violations = line[3:]
        active_const_v = []
        for const in constraints:
            active_const_v.append(violations[const - 1])
        grammar[letter][cand_num] = active_const_v
    return (grammar)

###############################################

### Run the main function
if __name__ == '__main__':
    main(eval_files_dir, constraints_file, targets_filename, iterations, rate, uni, override)
