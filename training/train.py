"""Train the recognizer on the GPU.

    uv run python train.py --name base --steps 60000
    uv run python train.py --name base --steps 60000 --resume

The training code is imported only here, under the main guard: the processes
that make the data re-import this file and must not load PyTorch.
"""

if __name__ == "__main__":
    from mathrec.training import main

    main()
