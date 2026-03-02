@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):

    # If user session does not exist → redirect to login
    if not request.session.get("user"):
        return RedirectResponse("/", status_code=303)

    return HTMLResponse(f"""
        <h2>Welcome {request.session['user']}</h2>
        <p>Role: {request.session['role']}</p>
        <a href="/logout">Logout</a>
    """)
    
    