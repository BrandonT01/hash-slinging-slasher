# 🩸 The Hash Slinging Slasher

As you all know, CoD asset names are hashed. Instead of storing something useful like `p9_rus_apartment_tower_sign_01`, the game stores a random string like `3b9dc0d01f2d2fce`.

I've been working on a way to attack this problem **at scale**, and it's already been tested successfully.

## What is it?

**The Hash Slinging Slasher** is a GitHub repo designed to find and resolve huge numbers of CoD asset hashes.

The goal is simple:

> **A community-powered hash-resolving farm.**

With enough people running it in their spare time, we could potentially resolve **the majority of the remaining hashes.**

## 🚨 You DON'T need the game

The game's **asset IDs are already captured in the repo**, so you don't need the actual game, Cordycep, Saluki, Windows, or a GPU.

All you need is:

* A computer
* The files from the repo
* Claude (or another coding agent)

Point your agent at the repo and say:

> **"Have a look at this repo and start grinding."**

That's it. It handles the rest.

Don't worry about burning through your usage either.

The actual hash searching is handled by compiled Rust code running directly on your CPU. The AI is only used to decide what to try and process the results.

You can leave it grinding for hours or overnight without chewing through your usage.

---

### 📤 Found hashes are submitted automatically

When it finds valid hashes, the tool **automatically submits them back to the GitHub repo** for everyone to benefit from.

You don't need to manually collect results or make GitHub commits - just let it run and it'll contribute what it finds.

## 🚀 Get involved

**Repo:**
https://github.com/KingslayerKyle/hash-slinging-slasher

If you've got a machine sitting around doing nothing, **put it to work.**

The more people running this, the faster we can turn thousands of meaningless hashes into actual, usable CoD asset names.
