# Delivery-only whitespace warning

The first terminal-publication attempt stopped before commit/QA because
`git diff --check` flagged the original frozen two-case input JSON's extra
blank line at EOF. Its exact SHA256is already part of the paid run identity;
removing that byte would be the wrong repair. The input is therefore explicitly
marked as nondiff/binary evidence while retaining all original bytes and its
hash. Source-code whitespace checks remain enabled. No model run, scientific
number, input definition, deadline or prior measurement was changed by this
delivery repair. The staged delivery is resumed only after verifying its base
commit and intended path scope; it is not deleted or reset.
