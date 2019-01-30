# A Gradual Learning Algorithm for Harmonic Grammar for letter strokes
# Written by Gali Ellenblum. Latest version: 2018-12-02

import sys
import random
import datetime
import numpy as np
import os
import glob
import operator
import re

##########################
## The main function that runs the GLA to find optimal HG weights for a given set of targets and constraint violations
def main(eval_files_dir, constraints, targets_filename, iterations, rate, uni, override):
    eval_files_letters = get_eval_files(eval_files_dir)
    filenames = eval_files_letters[0]
    letters = eval_files_letters[1]
    n_letters = len(letters)
    print 'Found %d active constraints' % (len(constraints))
    print 'Found %d characters in the %s folder' % (n_letters, eval_files_dir)

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
    logf = create_log_file(targets_filename, override)

    sum_of_relative_frequencies = sum(int(datum[2]) for datum in data)

    # Evaluate the data and adjust the weights for n iterations
    print 'Looking for optimal weights...'
    final_result = adjust_weights(iterations, data, grammar, weights, rate, sum_of_relative_frequencies, suppress = 0)

    full_success = write_summary(final_result, constraints, logf)
    failed_letters = find_failures(grammar, data, constraints, final_result, logf, full_success)
    logf.close()

    return(failed_letters)


###################################################
#           FUNCTIONS USED IN THIS SCRIPT         #
###################################################

# Initialize the weights
def initialize_weights(uni, constraints):
    if uni == 0:
        weights = np.random.random_sample(len(constraints)).tolist()
    elif uni == 1:
        weights = [1.0] * len(constraints)
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
    h_hash = {}
    outputs = grammar[pInput].keys()
    for o in outputs:
        h_hash[o] = harmony(grammar[pInput][o], weights)
    optimal_output = {}
    next_h = max(h_hash.values())
    min_h = -1000
    while len(optimal_output) < n_targets or next_h == min_h:
        max_t = max(h_hash.iteritems(), key = operator.itemgetter(1))[0]
        optimal_output[max_t] = h_hash[max_t]
        min_h = h_hash[max_t]
        h_hash[max_t] = -10000
        next_h = max(h_hash.values())
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
    error = np.round(map(float, error), 3)
    target = np.round(map(float, target), 3)
    v = np.subtract(error, target)
    v = np.multiply(v, rate)
    v = np.round(v, 2)
    return v


# Check if a given input matches the output
def update(datum, grammar, weights, rate):
    no_neg = 0 # Set to 1 to prohibit negative values; set to 0 to allow negative values
    pInput = datum[0]
    target = datum[1]
    output = optimize(weights, grammar, pInput, len(target))
    if set(output.keys()) == set(target):
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
            weights = np.add(weights, change_vector).tolist()
            if no_neg == 1:
                weights = [max(w, 0) for w in weights]
    return weights

# Evaluate the data on a given set of weights
def evaluate(weights, grammar, data):
    correct_count = 0
    for datum in data:
        targets = datum[1]
        output = optimize(weights, grammar, datum[0], len(targets)).keys()
        if set(output) == set(targets):
            correct_count += len(targets)
    accuracy = float(correct_count) / sum(n for (_, _,n) in data)
    #print 'ACCURACY is\t%s\n' % (str(accuracy))
    return (accuracy)

# Adjust the weights
def adjust_weights(iterations, data, grammar, weights, rate, sum_of_relative_frequencies, suppress):
    # Evaluate the data on the initial grammar
    initial_grammar = weights
    initial_grammar_text = 'INITIAL GRAMMAR:\t' + '\t'.join(map(str, [round(wt, 3) for wt in initial_grammar])) + '\n'
    print initial_grammar_text
    accuracy = evaluate(weights, grammar, data)
    max_accuracy = accuracy
    max_acc_iter = 0
    max_acc_wts = weights

    rand_seed = random.randint(1, 1000)
    #rand_seed = 562
    random.seed(rand_seed)

    if suppress == 0:
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
        elif s >= max(10*len(data), iterations, max_acc_s + max(250, iterations/4)):
            print '\nSampled %d times. Max accuracy first reached %d samples ago.\nStopping now.' % (s, s - max_acc_s)
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
                if suppress == 0:
                    print text
            else:
                1 == 1
            s += 1
    return ([max_accuracy, max_acc_iter, max_acc_wts, initial_grammar, max_acc_s, s, rand_seed])

# Create a log file - override=0 will create a new log for each run. 1 will create a new log once a day.
def create_log_file(targets_filename, override):
    if targets_filename[-4:] == '.txt':
        targets_filename = targets_filename[0:-4]
    now = datetime.datetime.now()
    counter = 1
    suff = re.compile('[nN][oO][a-zA-Z0-9]{1,6}\.txt')
    p_inits = re.compile('[A-Z]{3,3}_')
    p = p_inits.findall(targets_filename)
    if len(p) == 0:
        if targets_filename[0:3] == 'trg':
            base_name = targets_filename[3:]
        else:
            base_name = targets_filename
    else:
        suffix = suff.findall(targets_filename)
        if len(suffix) == 0:
            base_name = '%s' % (p[0][0:3])
        else:
            base_name = '%s_%s' % (p[0][0:3], suffix[0][0:-4])
    log_filename = 'Log_%s_%d-%d-%d_%d.txt' % (base_name, now.year, now.month, now.day, counter)
    if override == 1:
        logf = open(log_filename, 'w')
    else:
        while os.path.isfile(log_filename):
            counter += 1
            log_filename = 'Log_%s_%d-%d-%d_%d.txt' % (base_name, now.year, now.month, now.day, counter)
        logf = open(log_filename, 'w')
    return (logf)

# Write the best weights, max accuracy, and number of iterations to a log file
def write_summary(final_result, constraints, logf):
    # Get the best weights
    max_accuracy = final_result[0]
    max_acc_iter = final_result[1]
    max_acc_wts = final_result[2]
    initial_grammar = final_result[3]
    max_acc_s = final_result[4]
    rand_seed = final_result[6]

    # Print a summary of the maximum accuracy and the weights associated with it
    summary_text = '\nMax accuracy reached: %.2f\nMax accuracy first reached on iteration: %d (%d samples)\nRandom number generator initialized with seed %d\n' \
                   'Initial grammar weights:\t%s\nGrammar for max accuracy:\t%s\nConstraints:\t%s' \
                   % (max_accuracy, max_acc_iter, max_acc_s, rand_seed, '\t'.join(map(str, [round(wt, 2) for wt in initial_grammar])),
                      '\t'.join(map(str, [round(wt, 2) for wt in max_acc_wts])), '\t'.join(map(str, constraints)))
    logf.write(summary_text)
    print summary_text

    if max_accuracy == 1:
        return (1)
    else:
        return(0)

# Find and print which letters still fail after the specified number of iterations
def find_failures(grammar, data, constraints, final_result, logf, full_success):
    while True:
        #show_harmony = raw_input('\nWould you like to see the harmony and ranking of targets? Y/N\n').upper()
        show_harmony = 'N'
        if show_harmony not in ('Y', 'N'):
            print "Sorry, I didn\'t get that... "
            continue
        else:
            break
    best_weights = final_result[2]
    log_header = '\n\nLetter\tTarget\tHarmony\tRank\tN Cands\tCandidates tied with or ranked higher than the target\n'
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
            for cand in harmonies:
                if harmonies[cand] >= t_h and cand != t:
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
            letters_hg[(letter, t)] = (round(t_h, 3), rank, failures, len(grammar[letter]))
    if full_success == 1:
        print '\nALL DONE!!\n'
    else:
        print "\n\nThe following %d targets did not rank highest:\n" % (len(failed_letters))
        for failure in failed_letters:
            text = "Letter: %s\tTarget: %s\tCandidates ranked higher than (or tied with) the target:\t%s" % (failure[0], failure[1], '\t'.join(failure[2]))
            print text
        print '\nALL DONE!!\n'
    return(failed_letters)

#######################################
# Functions needed to format the data #
#######################################

# Get the list of eval file names and the list of participating letters from the directory
def get_eval_files(eval_dir):
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
                'Constraints file not found in %s.\nPress 1 to change directory or 2 to enter a new constraints filename: ' % const_path)
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
        #cand_code = line[0]
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

        # Get the list of active constraints
        constraints = get_constraints(constraints_file)

    main(eval_files_dir, constraints, targets_filename, iterations, rate, uni, override)
