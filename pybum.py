#!/usr/bin/env python

import os, config, sys, getopt
from PIL import Image
from jinja2 import Template
from boto.s3.connection import S3Connection
from boto.s3.key import Key
from boto.s3.bucket import Bucket
from keyring import get_password
from img_rotate import fix_orientation
import shutil

thumbsize = config.thumbsize
medsize = config.medsize
indexfile = config.indexfile
rssfile = config.rssfile
awsid = config.awsid
awsbucket = config.awsbucket

def help():
    print """
    usage: pybum.py [-r] action [album]
    """

def generate(source_album, target_album):
    if not os.path.exists(target_album):
        os.makedirs(target_album)

    images = os.listdir(source_album)
    print(source_album)
    
    index_html = target_album + '/index.html'
    album_name = target_album.split('_')[1:]
    album_title = ""
    for word in album_name:
        album_title = album_title + word + ' '
    if os.path.isfile(index_html):
        os.remove(index_html)
    f = open(index_html, 'a')
    f.write('<html><head><title>')
    f.write(album_title)
    f.write('''</title>
  <link type="text/css" rel="alternate stylesheet" media="screen,projection" title="colorbox" href="../shared/colorbox.css" />
  <link type="text/css" rel="stylesheet" media="screen,projection" title="default" href="../shared/default.css" />
  <link type="text/css" rel="alternate stylesheet" media="screen,projection" title="basic" href="../shared/basic.css" />
  <link rel="alternate" type="application/rss+xml" title="Recent galleries" href="index.xml" />
  <script type="text/javascript" src="../shared/jquery.js"></script>
  <script type="text/javascript" src="../shared/jquery.colorbox.js"></script>
  <script type="text/javascript" src="../shared/lazygal.js"></script>
  </head><body>
  <div class="media_links">
  <h2>''')
    f.write(album_title)
    f.write('''</h2>
  <a href="../">Home</a><br /><br />
    <ul class="thumbs noscript">
    ''' + '\n')
    for image in images:
        ratios = {'thumbnail':thumbsize, 'medium':medsize}
        for scale, size in ratios.iteritems():
            image_name = os.path.splitext(image)[0]
            image_extension = os.path.splitext(image)[1]
            outfile = target_album + '/' + image_name + "_" + scale + image_extension
            if not os.path.isfile(outfile):
                im = Image.open(source_album + '/' + image)
                im = fix_orientation(im, save_over=False)[0]
                im.thumbnail(size)
                print("creating {0}".format(outfile))
                im.save(outfile, "JPEG")
        f.write('  <li class="media media_image">' + '\n')
        f.write('    <a class="thumb" href="' + image_name + '_medium' + image_extension + '">')
        f.write('<img class="media media_image" src="' + image_name + '_thumbnail' + image_extension + '">')
        f.write('</a>' + '\n')
        f.write('  </li>' + '\n')
    f.write('</ul></div></body></html>')

def connectS3():
    awskey = get_password('aws-jnk', awsid)
    conn = S3Connection(awsid, awskey)
    bucket = conn.get_bucket(awsbucket)

def getParentIndex():
    pass

def getPrettyName(target_album):
    album_folder = target_album.split('/')
    album_folder = str(album_folder[-1:])
    album_folder = album_folder[2:-2]
    return album_folder

def writeMainIndex():
    albumlistindex = open(config.outdir + '/index.html', 'a')
    albumlistindex.write('''<html><head><title>Elebug Photos</title>
    <link type="text/css" rel="alternate stylesheet" media="screen,projection" title="colorbox" href="./shared/colorbox.css" />
    <link type="text/css" rel="stylesheet" media="screen,projection" title="default" href="./shared/default.css" />
    <link type="text/css" rel="alternate stylesheet" media="screen,projection" title="basic" href="./shared/basic.css" />
    <link rel="alternate" type="application/rss+xml" title="Recent galleries" href="index.xml" />
    <script type="text/javascript" src="./shared/jquery.js"></script>
    <script type="text/javascript" src="./shared/jquery.colorbox.js"></script>
    <script type="text/javascript" src="./shared/lazygal.js"></script>
    </head><body><ul>''' + '\n')

def publish(target_album):
    connectS3()
    getPrettyName(target_album)
    files = os.listdir(target_album)
    for file in files:
        k = Key(bucket)
        k.key = album_folder + '/' + file
        if not bucket.get_key(k.key):
            fullpath = target_album + '/' + file
            print("uploading " + fullpath + " to S3")
            k.set_contents_from_filename(fullpath)
    k = Key(bucket)
    k.key = album_folder + '/index.html'
    fullpath = target_album + '/index.html'
    k.set_contents_from_filename(fullpath)
    print("uploading album index to S3")
    albumlist = open(config.outdir + '/dirlist', 'a')
    albumlist.write(album_folder + '\n')
    albumlist.close()
    
    if os.path.isfile(config.outdir + 'index.html'):
        os.remove(config.outdir + 'index.html')
    
    albumlist = open(config.outdir + '/dirlist', 'r')
    albumlistuniq = open(config.outdir + '/dirlistuniq', 'w')
    lines = [line for line in albumlist]
    lines.sort(reverse=True)
    lines = set(lines)
    for line in lines:
    	albumlistuniq.write(line)
    albumlistuniq.close()
    albumlist = open(config.outdir + '/dirlistuniq', 'r')
    lines = [line for line in albumlist]
    lines.sort(reverse=True)
    writeMainIndex()
    for line in lines:
        album_name = line[:-1]
        album_name = album_name.split('_')[1:]
        album_title = ""
        for word in album_name:
            album_title = album_title + word + ' '
        album_date = line[:-1]
        album_date = album_date.split('_')[0:1]
        for date in album_date:
            album_date = date
        albumlistindex.write('<h2><a href="' + line[:-1] + '">' + album_title + '</a></h2>')
        albumlistindex.write('<p>' +  album_date + '</p>')
    albumlistindex.write('</ul></body></html>' + '\n')
    albumlistindex.close()
    k = Key(bucket)
    k.key = 'index.html'
    print("Uploading directory index to S3")
    k.set_contents_from_filename(config.outdir + '/index.html')
    shutil.move(config.outdir + '/dirlistuniq', config.outdir + '/dirlist')
    

def main(argv):
    
    opts, args = getopt.getopt(argv, "p:hlg:", ['publish=', "help", "list", "generate="])
    
    for opt, arg in opts:
        if opt in ('-h', '--help'):
            help()
            sys.exit()

        if opt in ('-l', '--list'):
            for item in os.listdir(config.sourcedir):
                if os.path.isdir(os.path.join(config.sourcedir, item)):
                	print item

        if opt in ('-g', '--generate'):
            source_album = config.sourcedir + arg
            target_album = config.outdir + arg
            generate(source_album, target_album)
        
        if opt in ('-p', '--publish'):
            target_album = config.outdir + arg
            publish(target_album)

if len(sys.argv) < 2:
    help()
    sys.exit(2)

main(sys.argv[1:])
