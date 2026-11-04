/**
 * jules-comment-classifier.cjs — Shared comment classification & filtering for all Jules workflows.
 *
 * This module replaces the inline, inconsistent skipMarkers/priorFeedback/priorReviews logic
 * that was duplicated across 6 workflows with 3 different marker arrays and no review-comment
 * filtering. See AUTOREVIEW_JULES_PLAN.md for the full design.
 *
 * Usage in actions/github-script@v7:
 *   const { classifyAndFilter, SOURCES, MARKERS } = require('./_helpers/.github/scripts/jules-comment-classifier.cjs');
 *   const result = await classifyAndFilter(github, owner, repo, prNumber, {
 *     includeReviewComments: true,   // fetch pulls.listReviewComments
 *     includeReviews: false,         // fetch pulls.listReviews
 *     includeThreads: false,         // fetch GraphQL reviewThreads (requires graphql permission)
 *     includeWalkthrough: false,     // if true, include jules-walkthrough comments in priorFeedback
 *     maxComments: 10,               // per surface
 *     maxBodyLength: 300,            // truncate bodies
 *   });
 *   // result.priorFeedback  — filtered issue comments (human/bot, Jules markers removed)
 *   // result.priorReviews   — filtered line-level review comments (Jules FINDING markers + bot authors removed)
 *   // result.julesContext   — Jules-generated content only (for address-comments workflow)
 *   // result.hasWalkthrough — boolean
 *   // result.reviews        — formal reviews (if includeReviews)
 *   // result.unresolvedThreads — GraphQL threads (if includeThreads)
 */

'use strict';

// ─── Constants ───────────────────────────────────────────────────────────────

const MARKERS = Object.freeze({
  JULES_REVIEWER:       '<!-- jules-pr-reviewer -->',
  JULES_AUTO_FIX:       '<!-- jules-auto-fix -->',
  JULES_AUTO_FIX_PLAN:  '<!-- jules-auto-fix-plan -->',
  JULES_AUTO_FIX_DENIED:'<!-- jules-auto-fix-plan-denied -->',
  JULES_AUTO_FIX_SUMMARY:'<!-- jules-auto-fix-summary -->',
  JULES_RESOLVE:        '<!-- jules-resolve -->',
  JULES_WALKTHROUGH:    '<!-- jules-walkthrough -->',
  JULES_REBUILD:        '<!-- jules-rebuild -->',
  JULES_QUOTA:          '<!-- jules-quota-exhausted -->',
  JULES_ADDRESS:        '<!-- jules-address-comments -->',
  FINDING:              '<!-- FINDING',
  WALKTHROUGH_START:    '<!-- walkthrough_start -->',
  WALKTHROUGH_END:      '<!-- walkthrough_end -->',
});

const ALL_JULES_MARKERS = Object.freeze([
  MARKERS.JULES_REVIEWER,
  MARKERS.JULES_AUTO_FIX,
  MARKERS.JULES_AUTO_FIX_PLAN,
  MARKERS.JULES_AUTO_FIX_DENIED,
  MARKERS.JULES_AUTO_FIX_SUMMARY,
  MARKERS.JULES_RESOLVE,
  MARKERS.JULES_WALKTHROUGH,
  MARKERS.JULES_REBUILD,
  MARKERS.JULES_QUOTA,
  MARKERS.JULES_ADDRESS,
]);

const THIRD_PARTY_MARKERS = Object.freeze([
  'sourcery-ai',
  '## Review Guide',
  '<!-- This is an auto-generated comment: summarize by',
  'coderabbit',
]);

const WALKTHROUGH_MARKERS = Object.freeze([
  MARKERS.JULES_WALKTHROUGH,
  MARKERS.WALKTHROUGH_START,
  ...THIRD_PARTY_MARKERS,
]);

const BOT_IDENTITIES = Object.freeze({
  JULES:         'google-labs-jules[bot]',
  GITHUB_ACTIONS: 'github-actions[bot]',
  DEPENDABOT:    'dependabot[bot]',
});

const SOURCES = Object.freeze({
  HUMAN:           'human',
  JULES_BOT:       'jules-bot',
  GITHUB_ACTIONS:  'github-actions',
  CODE_RABBIT:     'coderabbit',
  SOURCERY:        'sourcery',
  DEPENDABOT:      'dependabot',
  OTHER_BOT:       'other-bot',
  UNKNOWN:         'unknown',
});

// ─── Classification Functions ────────────────────────────────────────────────

function classifyAuthor(user) {
  if (!user || !user.login) return SOURCES.UNKNOWN;
  if (user.type === 'User') return SOURCES.HUMAN;
  if (user.login === BOT_IDENTITIES.JULES) return SOURCES.JULES_BOT;
  if (user.login === BOT_IDENTITIES.GITHUB_ACTIONS) return SOURCES.GITHUB_ACTIONS;
  if (user.login === BOT_IDENTITIES.DEPENDABOT) return SOURCES.DEPENDABOT;
  if (/coderabbit/i.test(user.login)) return SOURCES.CODE_RABBIT;
  if (/sourcery/i.test(user.login)) return SOURCES.SOURCERY;
  if (user.type === 'Bot') return SOURCES.OTHER_BOT;
  return SOURCES.UNKNOWN;
}

function classifyContent(body) {
  if (!body) return { hasJulesMarker: false, hasFinding: false, hasWalkthrough: false, hasSourcery: false, hasCodeRabbit: false, julesMarker: null };
  const hasJulesMarker = ALL_JULES_MARKERS.some(m => body.includes(m));
  const hasFinding = body.includes(MARKERS.FINDING);
  const hasWalkthrough = WALKTHROUGH_MARKERS.some(m =>
    m === MARKERS.WALKTHROUGH_END
      ? body.includes(m)
      : body.toLowerCase().includes(m.toLowerCase())
  );
  const hasSourcery = body.includes('sourcery-ai') || body.includes('## Review Guide');
  const hasCodeRabbit = /coderabbit/i.test(body);
  const julesMarker = ALL_JULES_MARKERS.find(m => body.includes(m)) || null;
  return { hasJulesMarker, hasFinding, hasWalkthrough, hasSourcery, hasCodeRabbit, julesMarker };
}

function isJulesGenerated(authorSource, contentClass) {
  if (authorSource === SOURCES.JULES_BOT) return true;
  if (authorSource === SOURCES.GITHUB_ACTIONS) {
    if (contentClass.hasJulesMarker || contentClass.hasWalkthrough) return true;
  }
  return false;
}

function formatAttribution(user) {
  const source = classifyAuthor(user);
  if (source === SOURCES.HUMAN) return user.login;
  return `[${user?.login || 'unknown'}]`;
}

// ─── Fetching Functions ──────────────────────────────────────────────────────

async function fetchIssueComments(github, owner, repo, prNumber) {
  const all = await github.paginate(github.rest.issues.listComments, {
    owner, repo, issue_number: prNumber, per_page: 100,
  });
  return all
    .sort((a, b) => new Date(b.created_at) - new Date(a.created_at))
    .map(c => ({
      id: c.id,
      user: c.user,
      authorSource: classifyAuthor(c.user),
      contentClass: classifyContent(c.body),
      body: c.body || '',
      createdAt: c.created_at,
      isJules: isJulesGenerated(classifyAuthor(c.user), classifyContent(c.body)),
    }));
}

async function fetchReviewComments(github, owner, repo, prNumber) {
  const all = await github.paginate(github.rest.pulls.listReviewComments, {
    owner, repo, pull_number: prNumber, per_page: 100,
  });
  return all.map(c => ({
    id: c.id,
    user: c.user,
    authorSource: classifyAuthor(c.user),
    contentClass: classifyContent(c.body),
    path: c.path,
    line: c.line,
    diffHunk: c.diff_hunk,
    body: c.body || '',
    createdAt: c.created_at,
    isJules: isJulesGenerated(classifyAuthor(c.user), classifyContent(c.body)),
  }));
}

async function fetchReviews(github, owner, repo, prNumber) {
  const all = await github.paginate(github.rest.pulls.listReviews, {
    owner, repo, pull_number: prNumber, per_page: 100,
  });
  return all.map(r => ({
    id: r.id,
    user: r.user,
    authorSource: classifyAuthor(r.user),
    contentClass: classifyContent(r.body),
    state: r.state,
    body: r.body || '',
    commitId: r.commit_id,
    createdAt: r.created_at,
    isJules: isJulesGenerated(classifyAuthor(r.user), classifyContent(r.body)),
  }));
}

async function fetchUnresolvedThreads(github, owner, repo, prNumber) {
  const threads = [];
  let threadCursor = null;
  do {
    const query = `
      query($owner: String!, $repo: String!, $pr: Int!, $threadCursor: String) {
        repository(owner: $owner, name: $repo) {
          pullRequest(number: $pr) {
            reviewThreads(first: 50, after: $threadCursor) {
              pageInfo { hasNextPage endCursor }
              nodes {
                isResolved
                comments(first: 100) {
                  nodes {
                    id
                    body
                    author { login __typename }
                    createdAt
                    path
                    diffHunk
                    originalLine
                  }
                }
              }
            }
          }
        }
      }`;
    const result = await github.graphql(query, { owner, repo, pr: prNumber, threadCursor });
    const rt = result.repository.pullRequest.reviewThreads;
    threads.push(...(rt.nodes || []));
    threadCursor = rt.pageInfo?.hasNextPage ? rt.pageInfo.endCursor : null;
  } while (threadCursor);

  return threads
    .filter(t => !t.isResolved)
    .map(t => {
      const nodes = t.comments.nodes || [];
      const last = nodes[nodes.length - 1];
      const authorLogin = last?.author?.login;
      const authorType = last?.author?.__typename || (authorLogin?.endsWith('[bot]') ? 'Bot' : 'User');
      return {
        isResolved: false,
        lastComment: last ? {
          id: last.id,
          author: authorLogin,
          authorSource: classifyAuthor({ login: authorLogin, type: authorType }),
          contentClass: classifyContent(last.body),
          body: last.body || '',
          path: last.path,
          line: last.originalLine,
          diffHunk: last.diffHunk,
          isJules: isJulesGenerated(
            classifyAuthor({ login: authorLogin, type: authorType }),
            classifyContent(last.body)
          ),
        } : null,
        allComments: nodes,
      };
    })
    .filter(t => t.lastComment !== null);
}

// ─── Main Entry Point ────────────────────────────────────────────────────────

async function classifyAndFilter(github, owner, repo, prNumber, opts = {}) {
  const {
    includeReviewComments = true,
    includeReviews = false,
    includeThreads = false,
    includeWalkthrough = false,
    maxComments = 10,
    maxBodyLength = 300,
  } = opts;

  // Use allSettled so optional fetch failures don't crash the whole workflow.
  const fetches = [
    { key: 'issueComments', promise: fetchIssueComments(github, owner, repo, prNumber) },
  ];
  if (includeReviewComments) fetches.push({ key: 'reviewComments', promise: fetchReviewComments(github, owner, repo, prNumber) });
  if (includeReviews) fetches.push({ key: 'reviews', promise: fetchReviews(github, owner, repo, prNumber) });
  if (includeThreads) fetches.push({ key: 'unresolvedThreads', promise: fetchUnresolvedThreads(github, owner, repo, prNumber) });

  const settled = await Promise.allSettled(fetches.map(f => f.promise));
  const results = {};
  fetches.forEach((f, i) => {
    if (settled[i].status === 'fulfilled') {
      results[f.key] = settled[i].value;
    } else {
      core?.warning?.(`Fetch failed for ${f.key}: ${settled[i].reason?.message || settled[i].reason}`);
      results[f.key] = [];
    }
  });

  const issueComments = results.issueComments || [];
  const reviewComments = results.reviewComments || [];
  const reviews = results.reviews || [];
  const unresolvedThreads = results.unresolvedThreads || [];

  // When includeWalkthrough is true, walkthrough comments are NOT filtered out
  // of priorFeedback (auto-fix wants walkthrough context).
  const excludeMarkers = includeWalkthrough
    ? ALL_JULES_MARKERS.filter(m => m !== MARKERS.JULES_WALKTHROUGH)
    : ALL_JULES_MARKERS;

  // ── priorFeedback: issue comments excluding Jules-generated content ──
  const priorFeedback = issueComments
    .filter(c => {
      if (excludeMarkers.some(m => c.body.includes(m))) return false;
      if (c.authorSource === SOURCES.JULES_BOT) return false;
      return true;
    })
    .slice(0, maxComments)
    .map(c => `${formatAttribution(c.user)}: ${c.body.slice(0, maxBodyLength)}`)
    .join('\n\n');

  // ── priorReviews: line-level review comments excluding Jules-generated content ──
  // THIS IS THE FIX for the defect documented in AUTOREVIEW_JULES_PLAN.md § 10.4.
  const priorReviews = reviewComments
    .filter(c => {
      if (c.authorSource === SOURCES.JULES_BOT) return false;
      if (c.authorSource === SOURCES.GITHUB_ACTIONS) return false;
      if (c.contentClass.hasFinding) return false;
      if (ALL_JULES_MARKERS.some(m => c.body.includes(m))) return false;
      return true;
    })
    .slice(0, maxComments)
    .map(c => `- ${c.path}:${c.line} — ${c.body.slice(0, maxBodyLength)}`)
    .join('\n');

  // ── julesContext: Jules-generated content only (for address-comments workflow) ──
  const julesContext = issueComments
    .filter(c => c.isJules)
    .slice(0, 3)
    .map(c => {
      const marker = c.contentClass.julesMarker || '';
      const label = marker.replace('<!-- ', '').replace(' -->', '');
      return `[${label}]\n${c.body.replace(/<!--.*?-->/g, '').trim().slice(0, 1500)}`;
    })
    .join('\n\n---\n\n');

  const julesReviewContext = reviews
    .filter(r => r.isJules)
    .slice(-3)
    .map(r => {
      const marker = r.contentClass.julesMarker || '';
      const label = marker.replace('<!-- ', '').replace(' -->', '');
      return `[${label}]\n${r.body.replace(/<!--.*?-->/g, '').trim().slice(0, 1500)}`;
    })
    .join('\n\n---\n\n');

  const allJulesContext = [julesContext, julesReviewContext].filter(Boolean).join('\n\n---\n\n');

  const hasWalkthrough = issueComments.some(c => c.contentClass.hasWalkthrough) ||
                         reviewComments.some(c => c.contentClass.hasWalkthrough);

  return {
    priorFeedback,
    priorReviews,
    julesContext: allJulesContext,
    hasWalkthrough,
    reviews: includeReviews ? reviews : undefined,
    unresolvedThreads: includeThreads ? unresolvedThreads : undefined,
    raw: {
      issueComments,
      reviewComments,
      reviews,
      unresolvedThreads,
    },
    _meta: {
      surfaces: ['issue-comments', ...(includeReviewComments ? ['review-comments'] : []),
                 ...(includeReviews ? ['reviews'] : []), ...(includeThreads ? ['threads'] : [])],
      includeWalkthrough,
      totalIssueComments: issueComments.length,
      totalReviewComments: reviewComments.length,
      julesIssueComments: issueComments.filter(c => c.isJules).length,
      julesReviewComments: reviewComments.filter(c => c.isJules).length,
      retainedReviewComments: reviewComments.length - reviewComments.filter(c => {
        return c.authorSource === SOURCES.JULES_BOT ||
               c.authorSource === SOURCES.GITHUB_ACTIONS ||
               c.contentClass.hasFinding ||
               ALL_JULES_MARKERS.some(m => c.body.includes(m));
      }).length,
    },
  };
}

// ─── Exports ─────────────────────────────────────────────────────────────────

module.exports = {
  MARKERS,
  ALL_JULES_MARKERS,
  THIRD_PARTY_MARKERS,
  WALKTHROUGH_MARKERS,
  BOT_IDENTITIES,
  SOURCES,
  classifyAuthor,
  classifyContent,
  isJulesGenerated,
  formatAttribution,
  classifyAndFilter,
};
