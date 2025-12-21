import { NextResponse } from "next/server";
import path from "path";
import { promises as fs } from "fs";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const uploadDir = path.join(process.cwd(), "public", "uploads");

async function ensureUploadDir() {
  await fs.mkdir(uploadDir, { recursive: true });
}

function isWithinUploadDir(targetPath: string) {
  const normalizedTarget = path.normalize(targetPath);
  const normalizedBase = path.normalize(uploadDir);
  return normalizedTarget.startsWith(normalizedBase);
}

export async function GET() {
  await ensureUploadDir();
  const files = await fs.readdir(uploadDir);

  const items = await Promise.all(
    files.map(async (name) => {
      const stats = await fs.stat(path.join(uploadDir, name));
      return {
        name,
        size: stats.size,
        modified: stats.mtime,
        url: `/uploads/${encodeURIComponent(name)}`,
      };
    })
  );

  return NextResponse.json({ files: items });
}

export async function POST(request: Request) {
  await ensureUploadDir();
  const formData = await request.formData();
  const file = formData.get("file");

  if (!file || !(file instanceof File)) {
    return NextResponse.json(
      { error: "A file is required under the `file` field." },
      { status: 400 }
    );
  }

  const arrayBuffer = await file.arrayBuffer();
  const buffer = Buffer.from(arrayBuffer);

  const safeName = file.name.replace(/[^a-zA-Z0-9._-]/g, "_");
  const filePath = path.join(uploadDir, safeName);

  if (!isWithinUploadDir(filePath)) {
    return NextResponse.json({ error: "Invalid file path." }, { status: 400 });
  }

  await fs.writeFile(filePath, buffer);

  return NextResponse.json({
    file: {
      name: safeName,
      size: buffer.byteLength,
      url: `/uploads/${encodeURIComponent(safeName)}`,
    },
  });
}

export async function DELETE(request: Request) {
  await ensureUploadDir();
  const { searchParams } = new URL(request.url);
  const fileName = searchParams.get("file");

  if (!fileName) {
    return NextResponse.json(
      { error: "Missing `file` query parameter." },
      { status: 400 }
    );
  }

  const filePath = path.join(uploadDir, fileName);
  if (!isWithinUploadDir(filePath)) {
    return NextResponse.json({ error: "Invalid file path." }, { status: 400 });
  }

  try {
    await fs.rm(filePath);
  } catch (error: any) {
    if (error?.code === "ENOENT") {
      return NextResponse.json({ error: "File not found." }, { status: 404 });
    }
    return NextResponse.json(
      { error: "Unable to delete file." },
      { status: 500 }
    );
  }

  return NextResponse.json({ ok: true });
}
