const form = document.getElementById("onboard");
if (form) {
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const result = document.getElementById("result");
    const fd = new FormData(form);
    const token = fd.get("token");
    fd.delete("token");
    const payload = Object.fromEntries(fd.entries());
    result.className = "";
    result.textContent = "Creating client…";
    try {
      const r = await fetch("/api/clients", {
        method:"POST",
        headers:{"Content-Type":"application/json","X-Admin-Token":token},
        body:JSON.stringify(payload)
      });
      const data = await r.json();
      if (!r.ok) throw new Error(data.detail || "Could not create client.");
      result.className = "ok";
      result.innerHTML = `Client created: <b>${data.business_name}</b> (ID ${data.id}). <a href="/">Open dashboard</a>`;
      form.reset();
    } catch (err) {
      result.className = "err";
      result.textContent = err.message;
    }
  });
}
