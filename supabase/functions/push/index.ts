// Filmrating: Push-Mitteilungen bei Freundschaftsanfragen und angenommenen Anfragen.
// GET  /push?action=key   -> öffentlicher Push-Schlüssel (wird beim ersten Aufruf erzeugt und in push_keys gespeichert)
// POST /push {type:'friendship', id}  -> vom Datenbank-Trigger aufgerufen
import webpush from "npm:web-push@3.6.7";
import { createClient } from "npm:@supabase/supabase-js@2";

const db = createClient(Deno.env.get("SUPABASE_URL")!, Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!);
const CORS = { "Access-Control-Allow-Origin": "*", "Access-Control-Allow-Headers": "authorization, apikey, content-type" };
const json = (b: unknown, s = 200) => new Response(JSON.stringify(b), { status: s, headers: { ...CORS, "Content-Type": "application/json" } });

async function keys() {
  const { data } = await db.from("push_keys").select("public_key, private_key").eq("id", 1).maybeSingle();
  if (data) return data;
  const k = webpush.generateVAPIDKeys();
  await db.from("push_keys").insert({ id: 1, public_key: k.publicKey, private_key: k.privateKey });
  const { data: again } = await db.from("push_keys").select("public_key, private_key").eq("id", 1).single();
  return again!;
}

async function sendTo(userId: string, title: string, body: string) {
  const k = await keys();
  webpush.setVapidDetails("https://liasoer.github.io/filmrating/", k.public_key, k.private_key);
  const { data: subs } = await db.from("push_subscriptions").select("endpoint, p256dh, auth").eq("user_id", userId);
  let sent = 0;
  for (const s of subs ?? []) {
    try {
      await webpush.sendNotification({ endpoint: s.endpoint, keys: { p256dh: s.p256dh, auth: s.auth } },
        JSON.stringify({ title, body, url: "/filmrating/?profil" }), { TTL: 86400 });
      sent++;
    } catch (e) {
      const code = (e as { statusCode?: number }).statusCode;
      if (code === 404 || code === 410) await db.from("push_subscriptions").delete().eq("endpoint", s.endpoint);
    }
  }
  return sent;
}

Deno.serve(async (req) => {
  if (req.method === "OPTIONS") return new Response(null, { headers: CORS });
  const url = new URL(req.url);
  if (req.method === "GET" && url.searchParams.get("action") === "key") return json({ publicKey: (await keys()).public_key });
  if (req.method !== "POST") return json({ error: "not found" }, 404);

  const { type, id } = await req.json().catch(() => ({}));
  if (type !== "friendship" || !id) return json({ error: "bad request" }, 400);

  // Daten immer selbst aus der Datenbank lesen, nie der Anfrage vertrauen
  const { data: f } = await db.from("friendships")
    .select("id, status, requester, addressee, r:profiles!friendships_requester_fkey(username), a:profiles!friendships_addressee_fkey(username)")
    .eq("id", id).maybeSingle();
  if (!f) return json({ skipped: "unknown" });

  // Jede Mitteilung nur einmal verschicken
  const { error: dup } = await db.from("push_log").insert({ friendship_id: f.id, status: f.status });
  if (dup) return json({ skipped: "already sent" });

  const r = (f.r as { username: string } | null)?.username ?? "jemand";
  const a = (f.a as { username: string } | null)?.username ?? "jemand";
  const sent = f.status === "pending"
    ? await sendTo(f.addressee, "Neue Freundschaftsanfrage", `@${r} möchte mit dir befreundet sein`)
    : await sendTo(f.requester, "Anfrage angenommen", `@${a} hat deine Freundschaftsanfrage angenommen`);
  return json({ sent });
});
