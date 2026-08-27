import { useEffect, useState } from "react"
import { BookOpen, ChevronRight, CircleAlert } from "lucide-react"
import { useSearchParams } from "react-router-dom"

import { getBrowseCategories } from "@/api/browse"
import BrowseBreadcrumbs from "@/components/BrowseBreadcrumbs"
import BrowseBranches from "@/components/BrowseBranches"
import BrowseSectionDetail from "@/components/BrowseSectionDetail"
import BrowseSectionList from "@/components/BrowseSectionList"
import {
  Alert,
  AlertDescription,
  AlertTitle,
} from "@/components/ui/alert"
import {
  Card,
  CardContent,
} from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"

/**
 * Browse provides deterministic navigation through the indexed
 * Immigration New Zealand Operational Manual.
 *
 * Unlike Ask, Browse does not use an LLM or retrieval ranking. The user
 * navigates through the taxonomy and section data exposed by the backend.
 *
 * Navigation hierarchy:
 * topic -> branch -> section list -> section detail
 */
function Browse() {
  const [searchParams, setSearchParams] = useSearchParams()

  // Browse categories come from /browse/categories so taxonomy labels,
  // descriptions, branches, and section counts remain backend-controlled.
  const [categories, setCategories] = useState([])

  // Request state for the initial category load.
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState(null)

  /*
   * Browse navigation is stored in the URL rather than local React state.
   *
   * This makes the current location bookmarkable and lets browser
   * Back/Forward navigation work naturally.
   */
  const selectedGroupId = searchParams.get("group")
  const selectedBranch = searchParams.get("branch")
  const selectedSection = searchParams.get("section")

  /*
   * Resolve the group id from the URL against the real taxonomy returned
   * by the backend.
   */
  const selectedGroup =
    categories.find((group) => group.id === selectedGroupId) ?? null

  /*
   * Validate the branch against the selected group's actual branch data.
   *
   * A branch name in the URL is not considered valid merely because the
   * parameter exists.
   */
  const selectedBranchData =
    selectedGroup?.branches.find(
      (branch) => branch.label === selectedBranch,
    ) ?? null

  /**
   * Load the Browse taxonomy when the page mounts.
   *
   * AbortController prevents an unfinished request from updating React state
   * if the user navigates away before the request completes.
   */
  useEffect(() => {
    const controller = new AbortController()

    async function loadCategories() {
      setIsLoading(true)
      setError(null)

      try {
        const data = await getBrowseCategories(controller.signal)

        setCategories(data)
      } catch (requestError) {
        /*
         * An aborted request is expected during component cleanup and should
         * not be shown to the user as an application failure.
         */
        if (requestError.name === "AbortError") {
          return
        }

        console.error(
          "Waypoint /browse/categories request failed:",
          requestError,
        )

        setError(
          "Waypoint could not load the Operational Manual topics. Please try again.",
        )
      } finally {
        /*
         * Do not update loading state after this request has been cancelled.
         */
        if (!controller.signal.aborted) {
          setIsLoading(false)
        }
      }
    }

    loadCategories()

    return () => {
      controller.abort()
    }
  }, [])

  /**
   * Keep the Browse URL consistent with the real backend taxonomy.
   *
   * Navigation is hierarchical:
   *
   * group -> branch -> section
   *
   * If a parent level is invalid or missing, dependent child parameters are
   * removed rather than allowing an impossible Browse state to render.
   */
  useEffect(() => {
    // Validation cannot happen until category data has finished loading.
    if (isLoading || error) {
      return
    }

    /*
     * A branch or section without a group is invalid.
     *
     * Example:
     * /browse?branch=Working+while+you+study
     *
     * Recover to:
     * /browse
     */
    if (!selectedGroupId) {
      if (selectedBranch || selectedSection) {
        setSearchParams({}, { replace: true })
      }

      return
    }

    /*
     * The group id does not exist in the current taxonomy.
     *
     * Example:
     * /browse?group=banana
     *
     * Recover to:
     * /browse
     */
    if (!selectedGroup) {
      setSearchParams({}, { replace: true })
      return
    }

    /*
     * A section cannot exist in the Browse hierarchy without a branch.
     *
     * Example:
     * /browse?group=study&section=U6.10
     *
     * Recover to:
     * /browse?group=study
     */
    if (!selectedBranch) {
      if (selectedSection) {
        setSearchParams(
          {
            group: selectedGroup.id,
          },
          {
            replace: true,
          },
        )
      }

      return
    }

    /*
     * The branch exists in the URL but does not belong to this group.
     *
     * Example:
     * /browse?group=study&branch=Skilled+Migrant+Category
     *
     * Recover to the valid group level.
     */
    if (!selectedBranchData) {
      setSearchParams(
        {
          group: selectedGroup.id,
        },
        {
          replace: true,
        },
      )
    }
  }, [
    isLoading,
    error,
    selectedGroupId,
    selectedGroup,
    selectedBranch,
    selectedBranchData,
    selectedSection,
    setSearchParams,
  ])

  /**
   * Return to the top whenever the user moves to another Browse level.
   *
   * Updating URL search parameters does not perform a traditional page
   * navigation, so browsers would otherwise preserve the previous scroll
   * position during the drill-down flow.
   */
  useEffect(() => {
    window.scrollTo({
      top: 0,
      behavior: "smooth",
    })
  }, [
    selectedGroupId,
    selectedBranch,
    selectedSection,
  ])

  /**
   * Select a top-level Browse topic.
   *
   * Starting a new topic clears any deeper branch or section state because
   * those values belong to the previous navigation path.
   */
  function handleGroupSelect(groupId) {
    setSearchParams({
      group: groupId,
    })
  }

  /**
   * Select a branch within the active group.
   *
   * Selecting a branch preserves the group but clears any section from a
   * previously selected branch.
   */
  function handleBranchSelect(branchLabel) {
    if (!selectedGroup) {
      return
    }

    setSearchParams({
      group: selectedGroup.id,
      branch: branchLabel,
    })
  }

  /**
   * Select one Operational Manual section.
   *
   * The group and branch remain in the URL so the complete Browse hierarchy
   * is preserved and can be reconstructed from a bookmarked URL.
   */
  function handleSectionSelect(sectionCode) {
    if (!selectedGroup || !selectedBranchData) {
      return
    }

    setSearchParams({
      group: selectedGroup.id,
      branch: selectedBranchData.label,
      section: sectionCode,
    })
  }

  /**
   * Recover when the section-detail endpoint reports an unknown section.
   *
   * Only the invalid section is removed. The already validated group and
   * branch remain selected, returning the user to the section list.
   */
  function handleInvalidSection() {
    if (!selectedGroup || !selectedBranchData) {
      return
    }

    setSearchParams(
      {
        group: selectedGroup.id,
        branch: selectedBranchData.label,
      },
      {
        replace: true,
      },
    )
  }

  return (
    <section className="mx-auto max-w-4xl">
      <p className="mb-2 text-sm font-semibold text-waypoint-blue">
        Explore the evidence
      </p>

      <h1 className="text-3xl font-semibold tracking-tight text-waypoint-navy sm:text-4xl">
        Browse the Operational Manual
      </h1>

      <p className="mt-4 max-w-2xl leading-7 text-muted-foreground">
        Browse the immigration instructions currently indexed by Waypoint.
        Choose a topic to explore the available sections.
      </p>

      {/*
        Breadcrumbs appear only after the user leaves the root Browse level.

        Earlier hierarchy levels are links. The current level is rendered as
        plain text so the user can always see where they are.
      */}
      <BrowseBreadcrumbs
        group={selectedGroup}
        branchLabel={selectedBranchData?.label}
        sectionCode={selectedSection}
      />

      <div className="mt-8">
        {/*
          Level 1: Topic selection.

          This is the only level shown when no valid group has been selected.
          Selecting a topic replaces these cards with its branches.
        */}
        {!selectedGroup && (
          <>
            <h2 className="text-lg font-semibold text-foreground">
              Choose a topic
            </h2>

            <p className="mt-1 text-sm leading-6 text-muted-foreground">
              Topics reflect Waypoint&apos;s human-facing organisation of the
              indexed Operational Manual.
            </p>

            {/* Initial category-load failure. */}
            {error && (
              <Alert variant="destructive" className="mt-5">
                <CircleAlert className="size-4" />

                <AlertTitle>Browse could not be loaded</AlertTitle>

                <AlertDescription>
                  {error}
                </AlertDescription>
              </Alert>
            )}

            {/*
              Skeleton cards reserve approximately the same layout while
              /browse/categories is loading.
            */}
            {isLoading && (
              <div className="mt-5 grid gap-4 md:grid-cols-2">
                {Array.from({ length: 4 }).map((_, index) => (
                  <Card key={index}>
                    <CardContent className="space-y-3 p-5">
                      <Skeleton className="size-10 rounded-full" />
                      <Skeleton className="h-5 w-2/3" />
                      <Skeleton className="h-3 w-full" />
                      <Skeleton className="h-3 w-4/5" />
                    </CardContent>
                  </Card>
                ))}
              </div>
            )}

            {/*
              Topic data is rendered directly from /browse/categories.
              No taxonomy labels or descriptions are duplicated in React.
            */}
            {!isLoading && !error && (
              <div className="mt-5 grid gap-4 md:grid-cols-2">
                {categories.map((group) => (
                  <Card
                    key={group.id}
                    className="transition-colors hover:border-waypoint-blue/50"
                  >
                    <CardContent className="p-0">
                      <button
                        type="button"
                        onClick={() => handleGroupSelect(group.id)}
                        className="flex w-full items-start gap-4 p-5 text-left"
                      >
                        <span
                          className="flex size-10 shrink-0 items-center justify-center rounded-full bg-waypoint-info-soft text-waypoint-info"
                          aria-hidden="true"
                        >
                          <BookOpen
                            className="size-5"
                            strokeWidth={1.8}
                          />
                        </span>

                        <span className="min-w-0 flex-1">
                          <span className="font-semibold text-foreground">
                            {group.label}
                          </span>

                          <span className="mt-1 block text-sm leading-6 text-muted-foreground">
                            {group.description}
                          </span>
                        </span>

                        <ChevronRight
                          className="mt-1 size-5 shrink-0 text-muted-foreground"
                          aria-hidden="true"
                        />
                      </button>
                    </CardContent>
                  </Card>
                ))}
              </div>
            )}
          </>
        )}

        {/*
          Level 2: Branch selection.

          A valid group exists, but no valid branch has been selected.
          Branches replace the topic cards in this same content area.
        */}
        {selectedGroup && !selectedBranchData && (
          <BrowseBranches
            group={selectedGroup}
            selectedBranch={null}
            onBranchSelect={handleBranchSelect}
          />
        )}

        {/*
          Level 3: Section list.

          Once both group and branch are valid, the branch cards are replaced
          with the matching Operational Manual section summaries.
        */}
        {selectedGroup &&
          selectedBranchData &&
          !selectedSection && (
            <BrowseSectionList
              groupId={selectedGroup.id}
              branch={selectedBranchData}
              selectedSection={null}
              onSectionSelect={handleSectionSelect}
            />
          )}

        {/*
          Level 4: Full section detail.

          The section list is replaced by the complete indexed section text.
          BrowseSectionDetail validates the section through the backend and
          reports a 404 back through onInvalidSection.
        */}
        {selectedGroup &&
          selectedBranchData &&
          selectedSection && (
            <BrowseSectionDetail
              sectionCode={selectedSection}
              onInvalidSection={handleInvalidSection}
            />
          )}
      </div>
    </section>
  )
}

export default Browse