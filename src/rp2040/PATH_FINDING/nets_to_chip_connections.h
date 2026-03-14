#pragma once

#include "path_mapping_algo.h"

// ---------------------------------------------------------------------------
// nets_to_chip_connections.h
//
// Stages 1-4 of the path-mapping pipeline:
//   1. bridgesToPaths()       — flatten net bridges into path[] array
//   2. findStartAndEndChips() — resolve which CH446Q chip(s) each node can reach
//   3. assignPathType()       — classify connection type, normalise node order
//   4. resolveChipCandidates()— pick a single chip per node (least-crowded)
//
// Call netsToChipConnections() to run all four in sequence.
// commitPaths() / sendAllPaths() (CH446Q SPI layer) come after.
// ---------------------------------------------------------------------------

// Running path count after the last bridgesToPaths() call.
extern int numberOfPaths;

// Return the nodeType enum for any logical node number.
nodeType getNodeType(int node);

// Stage 1 — copy net.bridges[][] into the flat path[] array.
int  bridgesToPaths();

// Stage 2 — populate path[i].candidates[0/1][0..2] for each path.
void findStartAndEndChips();

// Stage 3 — set path[i].pathType and normalise node order.
void assignPathType();

// Stage 4 — collapse candidates to a single chip[0]/chip[1] per path.
void resolveChipCandidates();

// Run stages 1-4 in order.
void netsToChipConnections();

// Stage 5 — fill path[i].x[]/y[] switch coordinates for each path.
void commitPaths();

// Stage 6 — resolve paths that needed multi-hop routing (altPathNeeded=1).
void resolveAltPaths();

// Stage 7 — add a parallel switch lane for every BBtoBB path to halve Ron.
void addParallelConnections();

// Run the full pipeline (stages 1-7) in one call.
void netsToChipConnectionsFull();
