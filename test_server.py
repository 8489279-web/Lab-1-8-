from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Lock
from time import sleep


class Handler(BaseHTTPRequestHandler):
    retry_count = 0
    retry_lock = Lock()

    def do_GET(self) -> None:
        if self.path == "/robots.txt":
            self.respond(
                "User-agent: *\nDisallow: /private",
                "text/plain",
            )
            return

        if self.path == "/retry":
            with Handler.retry_lock:
                Handler.retry_count += 1
                attempt = Handler.retry_count

            if attempt == 1:
                self.send_response(429)
                self.send_header("Retry-After", "1")
                self.send_header("Content-Length", "0")
                self.end_headers()
                return

            self.respond(
                "<html><title>Retry test</title>"
                "<body>Request completed successfully</body></html>"
            )
            return

        sleep(0.2)

        if self.path == "/":
            links = "".join(f'<a href="/page{i}">Page {i}</a>' for i in range(1, 251))
            self.respond(
                f"<html><title>Test website</title><body>{links}</body></html>"
            )

        elif self.path.startswith("/page"):
            number = self.path.removeprefix("/page")
            self.respond(
                f"<html><title>Document {number}</title>"
                f"<body>Python asyncio search engine "
                f"document {number}</body></html>"
            )

        else:
            self.send_error(404)

    def respond(
        self,
        content: str,
        content_type: str = "text/html",
    ) -> None:
        data = content.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()

        try:
            self.wfile.write(data)
        except (BrokenPipeError, ConnectionResetError):
            pass


if __name__ == "__main__":
    server = ThreadingHTTPServer(("127.0.0.1", 8000), Handler)
    print("Server running: http://127.0.0.1:8000")
    server.serve_forever()
