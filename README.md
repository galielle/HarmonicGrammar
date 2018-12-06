# HarmonicGrammar
Python code for Harmonic Grammar modeling of letter-strokes in writing

 - Run the main script HG_all1.py (which calls the latest version of HGlearn)
 - Constraints file should be formatted like MinConstEng.txt
    - constraints can have any name, as long as it does not have spaces (e.g., '1', or 'start_at_top')
 - Targets file should be formatted like trgEng.txt
    - multiple targets for the same character are required to all be ranked above non-targets, but there is no specification for internal order among targets
 - Eval files are tableaus of constraing violations for each candidate (generated automatically using MATLAB). See, e.g., Eval-Z-uc in the EvalFiles folder.
 - For example log file, see Log2018-12-2 (for 'hg' flag), or HGlog_MinusOne_trgEng (for 'MinusOne' flag)
