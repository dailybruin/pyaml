def squash_prefix(prefix: str, to_squash: str) -> str:
   def _squash_prefix(prefix: str, to_squash: str) -> str:
      if to_squash.startswith(prefix):
         return _squash_prefix(prefix, to_squash[len(prefix):])
      else:
         return prefix + to_squash

   if to_squash.startswith(prefix):
      return _squash_prefix(prefix, to_squash)
   else:
      return to_squash
