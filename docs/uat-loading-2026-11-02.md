# Explore search during loading

On the [merged docket preview](https://github.com/pranava0x0/datacenterwaterusage/commit/4aa98b5), a query entered while `graph-data.json` was loading stayed in the text box after the graph appeared, but the results list stayed empty. The [104-flow UAT](uat-2026-11-02.md) searched after the graph had loaded.

The [regression test](../tests/test_uat_site.py) rebuilds the site from source. It holds the graph request, enters `groundwater aquifer cooling discharge permit`, confirms the list is empty, then releases the request. It waits for the edge controls to appear independently of the first result card. Both viewport cases failed on the merged build: boot completed but no result appeared within three seconds. [Browser probe](../scripts/uat_site.py)

With the fix, phone (375×812) and desktop (1440×900) each displayed 12 results after one input event and one graph request. Both ranked “AWS LakeAnnaVA VPDES cooling discharge (2026)” first. The original flows and both delayed-request cases passed: **106 flows, zero failures**. [Local Chromium measurements and build hashes](uat-loading-2026-11-02.json)
