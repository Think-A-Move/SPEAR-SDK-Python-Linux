#!/usr/bin/env python3

import sys
import os
import re

def SearchFile(source, filename):
  if not os.path.isdir(source):
    return ''
  if not filename:
    return ''
  for subdir, dirs, files in os.walk(source):
    for f in files:
      if f == filename:
        return os.path.abspath(os.path.join(subdir, f))
  return ''
  
def ModifyConfig(f, source):
  if not os.path.isfile(f):
    print("file {} doesn't exist!".format(f)) 
  
  full_path = os.path.abspath(f)

  os.rename(full_path, '{}.bak'.format(full_path))

  lines = []
  with open('{}.bak'.format(full_path), 'r') as fh:
    for line in fh.readlines():
      ori_line = line
      line = line.strip()
      if line == "":
        continue
      # Pick config which includes the relative path
      if line[0] != '#' and '=' in line:
        comment = ''
        if '#' in line:
          line, comment = line.split('#', 1)
          comment = '#' + comment
         
        config_parameter, relative_conf_path = line[2:].split('=', 1)
        relative_conf_path = relative_conf_path.strip()
        new_location = SearchFile(source, os.path.basename(relative_conf_path))
        if new_location != '':
          lines.append("--{}={} {}\n".format(config_parameter, new_location, comment))
        else:
          lines.append("{} {}\n".format(line, comment))
        if ".conf" in new_location:
          ModifyConfig(new_location, source);
      else:
        lines.append(ori_line)
        
  with open(full_path, 'w') as fh:
    for line in lines:
      fh.write(line)
      #fh.write('\n')
  
  if os.path.isfile(full_path):
    if os.path.isfile('{}.bak'.format(full_path)):
      os.remove('{}.bak'.format(full_path))
  

def main():
  f_conf = sys.argv[1]
  source = sys.argv[2]
  ModifyConfig(f_conf, source)

if __name__ == '__main__':
  main()
