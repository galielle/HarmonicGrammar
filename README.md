# HarmonicGrammar
Python code for Harmonic Grammar modeling of letter-strokes in writing

 - Run the main script HG_all1.py (which calls the latest version of HGlearn)
 - Constraints file has the constraint name in column 1 and whether it is active or not in column 2. 
    - Constraints can have any name, as long as it does not have spaces (e.g., '1', or 'start_at_top')
    - See formatting in MinConstEng.txt
 - Targets file has the name of Eval file containing the letter name in column 1 (e.g., Eval-a-uc.txt), and the candidate numbers corresponding to the targets starting in column 2. 
    - See formatting in trgEng.txt
    - Multiple targets for the same character are required to all be ranked above non-targets, but there is no specification for internal order among targets
 - Eval files are tableaus of constraint violations for each candidate (generated automatically using MATLAB). See, e.g., Eval-Z-uc in the EvalFiles folder.
 - For example log file, see Log2018-12-2 (for 'hg' flag), or HGlog_MinusOne_trgEng (for 'MinusOne' flag)
