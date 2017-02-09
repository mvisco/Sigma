#!/bin/bash
#===============================================================================
#
#         FILE:  venv.sh
#
#        USAGE:  venv.sh
#                  or 
#                source venv.sh
#
#  DESCRIPTION:  This script runs virtualenv to set up the virtual enviroment
#                folder to contain the desired version of python as well as runs
#                pip to install packages specified in the requirements.txt file
#                in this same folder.
#
#        NOTES:  The first usage method will run the script but will not enter
#                into the virtual environment until explicitly invoked with the
#                activate command found within the virtualenv folder created by
#                by the script. The second method will run the script and
#                immediately enter the virtual environment. One additional note,
#                it was intentionally not written to use virtualenvwrapper due
#                to the desire to have this folder self-contained in 
#                anticipation of continuous integration. More information on
#                virtualenv is available here:  http://www.virtualenv.org/
#
# REQUIREMENTS:  This script requries virtualenv and pip are installed.
#
#===============================================================================

function die()
{
    echo "$1"
    exit 1
}

# Params for virtualenv, expected to be tweaked for your project needs.
VE_DIR=venv
VE_PYTHON='python2.7'
VE_PROMPT='(venv) '

# Run virtualenv to create the desired version of python.
virtualenv \
    --python "$VE_PYTHON" \
    --prompt "$VE_PROMPT" \
    --distribute \
    "$VE_DIR" \
    

# Activate the virtual environment.
source "$VE_DIR/bin/activate" 

# Run pip to installed required packages for this project.
pip install -r requirements.txt 

# If script was not sourced, remind the user.
if [ "$0" != "-bash" ]; then
    echo ""
    echo "Since you did not 'source' this script, be sure to activate your "
    echo "virtual environment before continuing. For example: "
    echo ""
    echo " source \"$VE_DIR/bin/activate\""
    echo ""
    echo "After activiation, simply run 'deactivate' in your shell to return "
    echo "your normal environment."
    echo ""
fi
