// Reverse-proxy Worker for chesscoach.nuezmiami.com -> HF Space.
// Free plan: 100k req/day, zero cold-start. No card required.
//
// Deploy (one-time, via dashboard):
//   1. Cloudflare dashboard -> Workers & Pages -> Create -> "Hello World" -> paste this file, Save & Deploy.
//   2. On the Worker page -> Settings -> Triggers -> Custom Domains -> Add
//      `chesscoach.nuezmiami.com` (delete the old Fly CNAME in DNS first).

const ORIGIN = 'https://nuezmiami-coach.hf.space';

export default {
  async fetch(request) {
    const url = new URL(request.url);
    const target = ORIGIN + url.pathname + url.search;
    const upstream = new Request(target, request);
    upstream.headers.set('Host', 'nuezmiami-coach.hf.space');
    upstream.headers.set('X-Forwarded-Host', url.host);
    const resp = await fetch(upstream);
    // strip HF's frame-busting so the page loads cleanly under our domain
    const headers = new Headers(resp.headers);
    headers.delete('content-security-policy');
    headers.delete('x-frame-options');
    return new Response(resp.body, {
      status: resp.status,
      statusText: resp.statusText,
      headers,
    });
  },
};
