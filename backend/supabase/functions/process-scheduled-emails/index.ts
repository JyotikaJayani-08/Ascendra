// Supabase Edge Function: process-scheduled-emails
//
// Called by pg_cron every 60 seconds.
// Hits your backend's internal endpoint to process due scheduled emails.
//
// Deploy: supabase functions deploy process-scheduled-emails
// Set secrets: supabase secrets set BACKEND_URL=https://your-backend.onrender.com INTERNAL_SECRET=your-jwt-secret

Deno.serve(async () => {
  const backendUrl = Deno.env.get("BACKEND_URL") || "http://localhost:8000";
  const internalSecret = Deno.env.get("INTERNAL_SECRET") || "";

  try {
    const response = await fetch(
      `${backendUrl}/api/v1/email/internal/process-scheduled`,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Internal-Secret": internalSecret,
        },
      }
    );

    const data = await response.json();
    console.log("Processed scheduled emails:", JSON.stringify(data));

    return new Response(JSON.stringify(data), {
      status: response.status,
      headers: { "Content-Type": "application/json" },
    });
  } catch (error) {
    console.error("Error processing scheduled emails:", error);
    return new Response(
      JSON.stringify({ error: (error as Error).message }),
      { status: 500, headers: { "Content-Type": "application/json" } }
    );
  }
});
