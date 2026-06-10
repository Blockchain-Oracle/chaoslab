import { notFound } from 'next/navigation'
import { RecipeView } from '@/components/artifacts/recipe-view'
import { PageShell } from '@/components/ui/page-shell'
import { fetchArtifactText, fetchRunDetail } from '@/lib/api'
import { parseRecipeMarkdown } from '@/lib/report-doc'

export const dynamic = 'force-dynamic'

interface PageProps {
  params: Promise<{ runId: string }>
}

export default async function RecipePage({ params }: PageProps) {
  const { runId } = await params
  const detail = await fetchRunDetail(runId)
  if (detail.status === 404) notFound()
  const run = detail.data?.run
  // A run with no recipe id never produced a hardening recipe — surfacing
  // an empty Surface G would be dishonest; bounce to the report page where
  // the run summary explains the outcome.
  if (run && !run.recipe_id) notFound()

  const downloadUrl = detail.data?.artifact_urls['recipe.md'] ?? null
  const recipeRes = downloadUrl
    ? await fetchArtifactText(downloadUrl)
    : { text: null, error: 'recipe.md not in the artifact set' }

  return (
    <PageShell label="recipe">
      <RecipeView
        runId={runId}
        recipeId={run?.recipe_id ?? null}
        recipeMd={recipeRes.text}
        recipeBlocks={recipeRes.text === null ? null : parseRecipeMarkdown(recipeRes.text)}
        recipeError={recipeRes.error}
        downloadUrl={downloadUrl}
        mrUrl={run?.mr_url ?? null}
        createdAt={run?.created_at ?? null}
        sample={run?.owner_uid === null}
      />
    </PageShell>
  )
}
