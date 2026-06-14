import { corsHeaders } from './cors.js';
import { handleTrigger } from './triggerWorkflow.js';
import { handleFinance } from './financeProxy.js';

export default {
  async fetch(request, env, ctx) {
    if (request.method === 'OPTIONS') {
      return new Response(null, { status: 204, headers: corsHeaders() });
    }

    const url = new URL(request.url);
    if (url.pathname === '/finance') {
      return handleFinance(request);
    }

    return handleTrigger(request, env);
  },
};
