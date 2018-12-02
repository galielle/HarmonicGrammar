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
import HGlearn11 as hg


def main():
    flags = ['hg', 'minusone', 'all']
    flag = get_flag(flags)

    while True:
        print "Default values for this script:\n" \
              "EvalFilesDirectory = current directory\n" \
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
        eval_files_dir = os.getcwd()
        iterations = 1000
        rate = 0.1  # change here, suggested 0.1
        uni = 0  # 0 = random initialization of weights; 1 = initialize all weights to 1.
    else:
        change_dir = raw_input('Change the directory of Eval files from current directory? (y/n) ').lower()
        if change_dir == 'n':
            eval_files_dir = os.getcwd()
        else:
            eval_files_dir = raw_input('Enter the directory where eval files are located: ')
        print "Eval files directory set to %s" % (eval_files_dir)
        iterations = int(raw_input('Enter the number of iterations: '))
        rate = float(raw_input('Enter the learning rate: '))
        uni = int(raw_input('Weights initialized to random values (0) or uniform values (1): '))

    if flag == 'hg':
        hg_letters = harmonic_grammar(eval_files_dir, iterations, rate, uni, override = 1) # Override = 0 to create a new logfile for each run

    elif flag == 'minusone':
        a = minusone(eval_files_dir, iterations, rate, uni)

    elif flag == 'all':
        great_success = run_all_hg(eval_files_dir, iterations, rate, uni)
        print great_success

    else:
        exit()


################

def get_flag(flags):
    not_flag = 'Use with one of the following options:\n" ' \
               'hg - calculate the optimal weights based on given constraints file and targets file\n' \
               'minusOne - run the script with one constraint fewer each time\n' \
               'all - run the script on all target files in a given directory\n'

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

def harmonic_grammar(eval_files_dir, iterations, rate, uni, override):
    ### Define basic parameters and get initial input
    constraints_file = raw_input('Enter the name of the constraints file: ')
    targets_filename = raw_input('Enter the name of the targets file: ')
    constraints = hg.get_constraints(constraints_file)

    # Run the hg script
    hg_letters = hg.main(eval_files_dir, constraints, targets_filename, iterations, rate, uni, override)
    return(hg_letters)


def minusone(eval_files_dir, iterations, rate, uni):
    eval_files_letters = hg.get_eval_files(eval_files_dir)
    filenames = eval_files_letters[0]

    # Get targets
    targets_filename = raw_input('Enter the name of the targets file: ')
    data = hg.get_data(targets_filename)
    print 'Found %d targets...\n' % (len(data))

    # Open a log file
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
    log_filename = 'HGlog_MinusOne_%s.txt' % (ID)
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

        max_accuracy = final_result[0]
        max_acc_iter = final_result[1]
        max_acc_wts = final_result[2]
        max_acc_s = final_result[4]

        # Print summary of maximum accuracy and weights associated with it
        summary_text = '\nMax accuracy reached: %.2f\nMax accuracy first reached on iteration: %d (%d samples)\nGrammar for max accuracy:\nWeights:\t%s\nConstraints:\t%s' \
                       % (max_accuracy, max_acc_iter, max_acc_s, '\t'.join(map(str, [round(wt, 2) for wt in max_acc_wts])),
                          '\t'.join(map(str, constraints)))
        logf.write(summary_text)
        print summary_text

        full_success = hg.write_summary(final_result, constraints, logf)
        failed_letters = hg.find_failures(grammar, data, constraints, final_result, logf,
                                          full_success)  # failed_letters = (letter, target, failures)
        if full_success == 1:
            1 == 1
        else:
            for failure in failed_letters:
                text = "\nLetter: %s\tTarget: %s\tCandidates ranked higher than (or tied with) the target:\t%s\n" % (
                    failure[0], failure[1], '\t'.join(failure[2]))

        max_acc_without[const] = (max_accuracy, max_acc_iter, max_acc_wts, failed_letters, max_acc_s)

    logf.write('\n\nSummary\nConstraint\tMax Accuracy\tIterations\tTotal Samples\tFailed Letters\n')
    for const in sorted(max_acc_without.keys()):
        logf.write('%s\t%.2f\t%d\t%d\t%s\n' % (const, max_acc_without[const][0], max_acc_without[const][1], max_acc_without[const][4],', '.join(failure[0] for failure in max_acc_without[const][3])))

    logf.close()


def run_all_hg(eval_files_dir, iterations, rate, uni):
    constraints = get_constraints(0)
    grammar = get_constraint_violations(eval_files_dir, constraints)

    ## Run the algorithm for each participant in a given folder
    target_dir = raw_input('Enter the directory with target files: ')
    target_files = get_target_files(target_dir)

    now = datetime.datetime.now()
    log_all_filename = 'all_HGlog_%d-%d-%d.txt' % (now.year, now.month, now.day)
    log_all = open(log_all_filename, 'w')

    all_results = {}

    for participant in sorted(target_files.keys()):
        data = hg.get_data(target_files[participant])
        print 'Found %d targets...\n' % (len(data))

        # Initialize weights
        weights = hg.initialize_weights(uni, constraints)

        # Open a log file
        log_filename = 'HGlog_%s_%d-%d-%d.txt' % (participant, now.year, now.month, now.day)
        logf = open(log_filename, 'w')

        sum_of_relative_frequencies = sum(int(datum[2]) for datum in data)

        # Evaluate the data and adjust the weights for n iterations
        print 'Looking for optimal weights for participant %s...' % (participant)
        final_result = hg.adjust_weights(iterations, data, grammar, weights, rate, sum_of_relative_frequencies, 0)

        max_accuracy = final_result[0]
        max_acc_iter = final_result[1]
        max_acc_wts = final_result[2]
        max_acc_s = final_result[4]
        total_s = final_result[5]

        # Print a summary of the maximum accuracy and the weights associated with it
        summary_text = '\nMax accuracy reached: %.2f\nMax accuracy first reached on iteration: %d (%d samples)\nGrammar for max accuracy:\nWeights:\t%s\nConstraints:\t%s' \
                       % (max_accuracy, max_acc_iter, max_acc_s, '\t'.join(map(str, [round(wt, 2) for wt in max_acc_wts])), '\t'.join(map(str, constraints)))
        log_all.write('Participant:\t%s%s' % (participant, summary_text))
        print summary_text

        full_success = hg.write_summary(final_result, constraints, logf)
        failed_letters = hg.find_failures(grammar, data, constraints, final_result, logf, full_success)  # failed_letters = (letter, target, failures)
        if full_success == 1:
            log_all.write('\n\n')
        else:
            for failure in failed_letters:
                text = "\nLetter: %s\tTarget: %s\tCandidates ranked higher than (or tied with) the target:\t%s\n" % (
                failure[0], failure[1], '\t'.join(failure[2]))
            log_all.write("%s\n\n" % (text))

        all_results[participant] = (max_accuracy, max_acc_iter, total_s, failed_letters)

        logf.close()

    text = "Participant\tMax Accuracy\tIteration for Max\tTotal Samples\n"
    print text
    log_all.write(text)
    for p in sorted(all_results.keys()):
        text = "%s\t%.2f\t%d\t%d" % (p, all_results[p][0], all_results[p][1], all_results[p][2])
        print text
        log_all.write('%s\n' % (text))
    log_all.close()

    return ("Great success")

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

def get_constraint_violations(eval_files_dir, constraints):
    eval_files_letters = hg.get_eval_files(eval_files_dir)
    filenames = eval_files_letters[0]
    letters = eval_files_letters[1]
    n_letters = len(letters)
    print 'Found %d active constraints' % (len(constraints))
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