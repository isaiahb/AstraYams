# POC: learn to position a part

## Goal

Demonstrate Astra identifying a policy failure, generating targeted learning experience, fine-tuning a policy, and measuring improvement.

## Task

A single robot arm pushes a free object into a target area and withdraws. No grasping, insertion, hidden attachment or prescribed object motion. Contact physics moves the object.

## Implementation order

1. Import the robot into MuJoCo; verify geometry, joint control and contact behavior.
2. Add a workbench, a free part, target, camera and repeatable randomized resets.
3. Freeze a geometric success test: object footprint inside target, low residual speed, and tool withdrawn for a declared hold interval.
4. Record physics-executed demonstrations and train an initial small policy.
5. Diagnose development-set failures; generate targeted examples and fine-tune.
6. Evaluate both checkpoints on the same untouched test cases. Record failures as well as successes.
7. Show before/after video, learning evidence and the agent’s actual changes.

## Model contract

Start with a compact policy for a reliable local training experiment. Test a pretrained VLA separately if practical; label state-based, visual and VLA results accurately. Define all observation/action units and normalization before collecting data.

## Evidence

Version scene, reward, evaluator, dataset and checkpoints. Keep train/development/test splits separate. Report n/N success, force violations, cycle time and compute. Changes to the evaluator require rerunning both candidates. No success or improvement is claimed until measured.
