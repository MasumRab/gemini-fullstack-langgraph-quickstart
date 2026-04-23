Rebased the following PRs on main:
#306, #305, #304, #303, #301, #294, #354, #353, #352, #350.

Method used:
For each PR, a new branch was created from main, the PR was merged using --allow-unrelated-histories and -Xtheirs to resolve conflicts in favor of the PR (due to divergent roots in the repository), and then squashed into a single clean commit on top of main. The resulting branches were pushed to origin as pr-350. All PRs are now mergeable with origin/main.
