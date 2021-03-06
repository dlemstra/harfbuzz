#!/usr/bin/env python3

import sys, os, subprocess, hashlib, tempfile, shutil

def cmd(command):
	global process
	process.stdin.write ((' '.join (command) + '\n').encode ("utf-8"))
	process.stdin.flush ()
	return process.stdout.readline().decode ("utf-8").strip ()

args = sys.argv[1:]

reference = False
if len (args) and args[0] == "--reference":
	reference = True
	args = args[1:]

no_ft_funcs = bool(int(os.getenv ('NO_FT_FUNCS', '0')))

if not args or args[0].find('hb-shape') == -1 or not os.path.exists (args[0]):
	sys.exit ("""First argument does not seem to point to usable hb-shape.""")
hb_shape, args = args[0], args[1:]

process = subprocess.Popen ([hb_shape, '--batch'],
			    stdin=subprocess.PIPE,
			    stdout=subprocess.PIPE,
			    stderr=sys.stdout)

passes = 0
fails = 0
skips = 0

if not len (args):
	args = ['-']

for filename in args:
	if not reference:
		if filename == '-':
			print ("Running tests from standard input")
		else:
			print ("Running tests in " + filename)

	if filename == '-':
		f = sys.stdin
	else:
		f = open (filename, encoding='utf8')

	for line in f:
		comment = False
		if line.startswith ("#"):
			comment = True
			line = line[1:]

			if line.startswith (' '):
				if not reference:
					print ("#%s" % line)
				continue

		line = line.strip ()
		if not line:
			continue

		fontfile, options, unicodes, glyphs_expected = line.split (":")
		options = options.split ()
		if fontfile.startswith ('/') or fontfile.startswith ('"/'):
			if os.name == 'nt': # Skip on Windows
				continue

			fontfile, expected_hash = fontfile.split('@')

			try:
				with open (fontfile, 'rb') as ff:
					actual_hash = hashlib.sha1 (ff.read()).hexdigest ().strip ()
					if actual_hash != expected_hash:
						print ('different version of %s found; Expected hash %s, got %s; skipping.' %
							   (fontfile, expected_hash, actual_hash))
						skips += 1
						continue
			except:
				print ('%s not found, skip.' % fontfile)
				skips += 1
				continue
		else:
			cwd = os.path.dirname(filename)
			fontfile = os.path.normpath (os.path.join (cwd, fontfile))

		extra_options = ["--shaper=ot"]
		if glyphs_expected != '*':
			extra_options.append("--verify")

		if comment:
			if not reference:
				print ('# %s "%s" --unicodes %s' % (hb_shape, fontfile, unicodes))
			continue

		if not reference:
			print ('%s "%s" %s %s --unicodes %s' %
					 (hb_shape, fontfile, ' '.join(extra_options), options, unicodes))

		# hack to support fonts with space on run-tests.py, after several other tries...
		if ' ' in fontfile:
			new_fontfile = os.path.join (tempfile.gettempdir (), 'tmpfile')
			shutil.copyfile(fontfile, new_fontfile)
			fontfile = new_fontfile

		if "--font-funcs=ft" in options and no_ft_funcs:
			skips += 1
			continue

		if "--font-funcs=ot" in options or no_ft_funcs:
			glyphs1 = cmd ([hb_shape, "--font-funcs=ot", fontfile] + extra_options + ["--unicodes", unicodes] + options)
		else:
			glyphs1 = cmd ([hb_shape, "--font-funcs=ft", fontfile] + extra_options + ["--unicodes", unicodes] + options)
			glyphs2 = cmd ([hb_shape, "--font-funcs=ot", fontfile] + extra_options + ["--unicodes", unicodes] + options)

			if glyphs1 != glyphs2 and glyphs_expected != '*':
				print ("FT funcs: " + glyphs1, file=sys.stderr)
				print ("OT funcs: " + glyphs2, file=sys.stderr)
				fails += 1
			else:
				passes += 1

		if reference:
			print (":".join ([fontfile, " ".join(options), unicodes, glyphs1]))
			continue

		if glyphs1.strip() != glyphs_expected and glyphs_expected != '*':
			print ("Actual:   " + glyphs1, file=sys.stderr)
			print ("Expected: " + glyphs_expected, file=sys.stderr)
			fails += 1
		else:
			passes += 1

if not reference:
	print ("%d tests passed; %d failed; %d skipped." % (passes, fails, skips), file=sys.stderr)
	if not (fails + passes):
		print ("No tests ran.")
	elif not (fails + skips):
		print ("All tests passed.")

if fails:
	sys.exit (1)
elif passes:
	sys.exit (0)
else:
	sys.exit (77)
