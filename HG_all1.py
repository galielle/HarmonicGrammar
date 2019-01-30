# Written by Gali Ellenblum. Latest version: 2018-12-02
# This script calls the latest version of HGlearn, and runs the GLA for HG in one of three modes:
# hg - one set of targets and one set of constraints
# minusone - one set of targets, removing one constraint from the given set each time
# all - on each file beginning with "trg" in a given folder (i.e., for all participants in a folder)

import sys
import re
import random
import datetime
import numpy as np
import os
import glob
import HGlearn12 as hg

######

## The main function, calling the scripts that either run the GLA normally, remove one constraint at a time,
## or run consecutively for all participant files in a directory

def main():
    flags = ['hg', 'minusone', 'all', 'countcands']
    flag = get_flag(flags)

    while True:
        print "Default values for this script:\n" \
              "Iterations = 1000\n" \
              "Rate of learning = 0.1\n" \
              "Weights initialized to random values\n"
        default_vals = raw_input('Would you like to use the default values (y) or re-define them (n)?\n ').lower()
        if default_vals not in ('y', 'n'):
            print "Sorry, I didn\'t get that... "
            continue
        else:
            break
    if default_vals == 'y':
        iterations = 1000
        rate = 0.1  # change here, suggested 0.1
        uni = 0  # 0 = random initialization of weights; 1 = initialize all weights to 1.
    else:
        iterations = int(raw_input('Enter the number of iterations: '))
        rate = float(raw_input('Enter the learning rate: '))
        uni = int(raw_input('Weights initialized to random values (0) or uniform values (1): '))

    change_dir = raw_input('Change the directory of Eval files from current directory? (y/n) ').lower()
    if change_dir == 'n':
        eval_files_dir = os.getcwd()
    else:
        eval_files_dir = raw_input('Enter the directory where eval files are located: ')
    print "Eval files directory set to %s" % (eval_files_dir)

    if flag == 'hg':
        hg_letters = harmonic_grammar(eval_files_dir, iterations, rate, uni, override = 0) # Override = 0 to create a new logfile for each run

    elif flag == 'minusone':
        minus1 = minusone(eval_files_dir, iterations, rate, uni)

    elif flag == 'all':
        great_success = run_all_hg(eval_files_dir, iterations, rate, uni)
        print great_success

    elif flag == 'countcands':
        cand_nums = count_cands(eval_files_dir)


    else:
        exit()

################

# Get the user-selected flag to decide which version to run
def get_flag(flags):
    not_flag = 'Use with one of the following options:\n' \
               'hg - calculate the optimal weights based on given constraints file and targets file\n' \
               'minusOne - run the script removing one of the constraints each time\n' \
               'all - run the script on all target files in a given directory\n' \
               'countCands - return the number of candidates for each letter-shape and for all of the letter shapes in a given targets file'

    if len(sys.argv) != 2:
        print not_flag
        while True:
            flag = raw_input('Choose option: ').lower()
            if flag not in flags:
                print "Sorry, I didn\'t get that..."
                continue
            else:
                break

    else:
        flag = sys.argv[1].lower()
        if flag not in flags:
            print not_flag
            while True:
                flag = raw_input('Choose option: ').lower()
                if flag not in flags:
                    print "Sorry, I didn\'t get that..."
                    continue
                else:
                    break
    return(flag)


####################

## Calls the main function from the latest version of the HGlearn script
def harmonic_grammar(eval_files_dir, iterations, rate, uni, override):
    ### Define basic parameters and get initial input
    constraints_file = raw_input('Enter the name of the constraints file: ')
    targets_filename = raw_input('Enter the name of the targets file: ')
    constraints = hg.get_constraints(constraints_file)

    # Run the hg script
    hg_letters = hg.main(eval_files_dir, constraints, targets_filename, iterations, rate, uni, override)
    return(hg_letters)

## Runs the GLA removing one constraint each time, to find the maximum success with each subset of constraints
def minusone(eval_files_dir, iterations, rate, uni):
    eval_files_letters = hg.get_eval_files(eval_files_dir)
    filenames = eval_files_letters[0]

    # Get targets
    targets_filename = raw_input('Enter the name of the targets file: ')
    data = hg.get_data(targets_filename)
    print 'Found %d targets...\n' % (len(data))

    # Open a log file
    ID = determine_id(targets_filename)
    now = datetime.datetime.now()
    log_filename = 'HGlog_MinusOne_%d-%d-%d_%s.txt' % (now.year, now.month, now.day, ID)

    logf = open(log_filename, 'w')
    logf.write('%s\n' % (ID))

    all_constraints = get_constraints(0)
    suppress = 1

    max_acc_without = {}

    # Get violations without one constraint each time
    for const in all_constraints:
        logf.write('\n\n')
        constraints = [c for c in all_constraints if c != const]
        print 'Analyzing constraint violations without constraint number %s\n' % (const)
        logf.write('Results without constraint %s\n' % (const))
        grammar = {}
        for eval_filename in filenames:
            grammar = hg.write_letter(eval_filename, constraints, grammar)
        print 'All done with constraint violations!\n'

        # Initialize weights
        weights = hg.initialize_weights(uni, constraints)

        sum_of_relative_frequencies = sum(int(datum[2]) for datum in data)

        # Evaluate the data and adjust the weights for n iterations
        final_result = hg.adjust_weights(iterations, data, grammar, weights, rate, sum_of_relative_frequencies, suppress)

        full_success = hg.write_summary(final_result, constraints, logf)
        failed_letters = hg.find_failures(grammar, data, constraints, final_result, logf,
                                          full_success)  # failed_letters = (letter, target, failures)

        max_accuracy = final_result[0]
        max_acc_iter = final_result[1]
        max_acc_wts = final_result[2]
        max_acc_s = final_result[4]

        max_acc_without[const] = (max_accuracy, max_acc_iter, max_acc_wts, failed_letters, max_acc_s)

    logf.write('\n\nSummary\nConstraint\tMax Accuracy\tIterations\tTotal Samples\tFailed Letters\n')
    print '\n\nSummary\nConstraint\tMax Accuracy\tIterations\tTotal Samples\tFailed Letters\n'
    for const in sorted(max_acc_without.keys()):
        text = '%s\t%.2f\t%d\t%d\t%s\n' % (const, max_acc_without[const][0], max_acc_without[const][1], max_acc_without[const][4],', '.join(failure[0] for failure in max_acc_without[const][3]))
        logf.write(text)
        print text

    logf.close()

# Runs the GLA with the same parameters on each of the participant files in a given directory
def run_all_hg(eval_files_dir, iterations, rate, uni):
    constraints = get_constraints(0)
    grammar = get_constraint_violations(eval_files_dir, constraints)

    ## Run the algorithm for each participant in a given folder
    target_dir = raw_input('Enter the directory with target files: ')
    target_files = get_target_files(target_dir)

    now = datetime.datetime.now()
    counter = 1
    log_all_filename = 'all_HGlog_%d-%d-%d_%d.txt' % (now.year, now.month, now.day, counter)
    while os.path.isfile(log_all_filename):
        counter += 1
        log_all_filename = 'all_HGlog_%d-%d-%d_%d.txt' % (now.year, now.month, now.day, counter)
    log_all = open(log_all_filename, 'w')

    all_results = {}

    for participant in sorted(target_files.keys()):
        data = hg.get_data(target_files[participant])
        print 'Found %d targets...\n' % (len(data))

        # Open a log file
        log_filename = 'HGlog_%s_%d-%d-%d.txt' % (participant, now.year, now.month, now.day)
        logf = open(log_filename, 'w')

        p_accuracy = 0
        n = 1
        while p_accuracy < 1 and n <= 3:
            logf.write('Participant:\t%sAttempt:\t%d\n' % (participant, n))

            # Initialize weights
            weights = hg.initialize_weights(uni, constraints)

            sum_of_relative_frequencies = sum(int(datum[2]) for datum in data)

            # Evaluate the data and adjust the weights for n iterations
            print 'Looking for optimal weights for participant %s...' % (participant)
            final_result = hg.adjust_weights(iterations, data, grammar, weights, rate, sum_of_relative_frequencies, 0)

            max_accuracy = final_result[0]
            max_acc_iter = final_result[1]
            max_acc_wts = final_result[2]
            initial_grammar = final_result[3]
            max_acc_s = final_result[4]
            total_s = final_result[5]
            rand_seed = final_result[6]

            # Print a summary of the maximum accuracy and the weights associated with it
            summary_text = '\nMax accuracy reached: %.2f\nMax accuracy first reached on iteration: %d (%d samples)\nRandom number generator initialized with seed %d\nInitial grammar weights:\t%s\nGrammar for max accuracy:\t%s\nConstraints:\t%s' \
                           % (max_accuracy, max_acc_iter, max_acc_s, rand_seed,
                              '\t'.join(map(str, [round(wt, 2) for wt in initial_grammar])),
                              '\t'.join(map(str, [round(wt, 2) for wt in max_acc_wts])), '\t'.join(map(str, constraints)))
            log_all.write('Participant:\t%s\tAttempt:\t%d' % (participant, n))
            log_all.write('%s' % summary_text)
            logf.write(summary_text)
            print summary_text

            failed_letters = hg.find_failures(grammar, data, constraints, final_result, logf, max_accuracy)  # failed_letters = (letter, target, failures)
            if max_accuracy == 1:
                log_all.write('\n\n')
            else:
                log_all.write('\nLetter\tTarget\tCandidates ranked higher than (or tied with) the target\n')
                for failure in failed_letters:
                    text = "%s\t%s\t%s\n" % (failure[0], failure[1], '\t'.join(failure[2]))
                log_all.write("%s\n\n" % (text))

            if max_accuracy > p_accuracy:
                p_accuracy = max_accuracy
                all_results[participant] = (max_accuracy, max_acc_iter, total_s, failed_letters, rand_seed)

            n += 1

        logf.close()

    text = "Participant\tMax Accuracy\tIteration for Max\tTotal Samples\tRandom Seed\tFailed Letters\n"
    print text
    log_all.write(text)
    for p in sorted(all_results.keys()):
        text = "%s\t%.2f\t%d\t%d\t%d\t%s" % (p, all_results[p][0], all_results[p][1], all_results[p][2], all_results[p][4], ','.join(set([f[0] for f in all_results[p][3]])))
        print text
        log_all.write('%s\n' % (text))
    log_all.close()

    return ("Great success")

# Prints a file containing the number of candidates for each letter
def count_cands(eval_files_dir):
    constraints_filename = 'AllConst'
    targets_filename = raw_input('Enter the name of the targets file: ')
    constraints = hg.get_constraints(constraints_filename)
    grammar = get_constraint_violations(eval_files_dir, constraints)

    data = hg.get_data(targets_filename)

    now = datetime.datetime.now()
    counter = 1
    log_filename = 'Log_CandCounts_%d-%d-%d_%d.txt' % (now.year, now.month, now.day, counter)
    while os.path.isfile(log_filename):
        counter += 1
        log_filename = 'Log_CandCounts_%d-%d-%d_%d.txt' % (now.year, now.month, now.day, counter)
    logf = open(log_filename, 'w')

    for datum in data:
        letter = datum[0]
        n_targets = datum[2]
        cands = grammar[letter]
        logf.write('%s\t%d\t%d\n' % (letter, n_targets, len(cands)))
        print letter, n_targets, len(cands)


    return 'success'

# Finds the ID of a target file
def determine_id(targets_filename):
    if targets_filename[-4:] == '.txt':
        ID = targets_filename[:-4]
    else:
        ID = targets_filename
    if ID[:3] == 'trg':
        ID = ID[3:]
    if ID[0] == '_':
        ID = ID[1:]
    else:
        ID = ID
    return(ID)

# Gets all the target files from a given directory
def get_target_files(target_dir):
    os.chdir(target_dir)
    participant_files = {}
    all_files = glob.glob("trg*.txt")
    regex = re.compile('[nN][oO][a-zA-Z0-9]{1,6}\.')
    p_inits = re.compile('[A-Z]{3,3}_')
    target_files = [file for file in all_files if p_inits.findall(file) and not regex.search(file)]
    for file in target_files:
        p = p_inits.findall(file)[0][0:3]
        participant_files[p] = file

    return (participant_files)

# Gets all the constraints from an active constraints file
def get_constraints(all):
    # Get constraints and violations
    if all == 1:
        constraints_filename = 'AllConst'
    else:
        while True:
            all_const = raw_input('Use default constraints file (AllConst)? y/n ').lower()
            if all_const not in ('y', 'n'):
                print 'Sorry, I didn\'t get that...'
                continue
            else:
                break
        if all_const == 'y':
            constraints_filename = 'AllConst'
        else:
            constraints_filename = raw_input('Enter a new constraints filename: ')
    constraints = hg.get_constraints(constraints_filename)
    print 'Found %d active constraints' % (len(constraints))
    return(constraints)

# Gets all constraint violations from a directory containing eval files
def get_constraint_violations(eval_files_dir, constraints):
    eval_files_letters = hg.get_eval_files(eval_files_dir)
    filenames = eval_files_letters[0]
    letters = eval_files_letters[1]
    n_letters = len(letters)
    #print 'Found %d active constraints' % (len(constraints))
    print 'Found %d characters in the %s folder' % (n_letters, eval_files_dir)

    # Get violations
    print 'Analyzing constraint violations...'
    grammar = {}
    for eval_filename in filenames:
        grammar = hg.write_letter(eval_filename, constraints, grammar)
    print 'All done with constraint violations!\n'
    return(grammar)

### Run the main function
if __name__ == '__main__':
    main()
